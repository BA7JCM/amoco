#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2013 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

import pyparsing as pp

from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")
# logger.level = 10

from amoco.arch.sparc.cpu_v8 import instruction_sparc as instruction
from amoco.arch.sparc import env


# ------------------------------------------------------------------------------
# parser for sparc assembler syntax.
class sparc_syntax:
    divide = False
    noprefix = False

    comment = pp.Regex(r"\#.*")
    symbol = pp.Regex(r"[A-Za-z_.$][A-Za-z0-9_.$]*").setParseAction(
        lambda r: env.ext(r[0], size=32)
    )
    mnemo = pp.LineStart() + symbol + pp.Optional(pp.Literal(",a"))
    mnemo.setParseAction(lambda r: r[0].ref.lower() + "".join(r[1:]))
    integer = pp.Regex(r"[1-9][0-9]*").setParseAction(lambda r: int(r[0], 10))
    hexa = pp.Regex(r"0[xX][0-9a-fA-F]+").setParseAction(lambda r: int(r[0], 16))
    octa = pp.Regex(r"0[0-7]*").setParseAction(lambda r: int(r[0], 8))
    bina = pp.Regex(r"0[bB][01]+").setParseAction(lambda r: int(r[0], 2))
    char = pp.Regex(r"('.)|('\\\\)").setParseAction(lambda r: ord(r[0]))
    number = integer | hexa | octa | bina | char
    number.setParseAction(lambda r: env.cst(r[0], 32))

    term = symbol | number

    exp = pp.Forward()

    op_one = pp.oneOf("- ~")
    op_sig = pp.oneOf("+ -")
    op_mul = pp.oneOf("* /")
    op_cmp = pp.oneOf("== != <= >= < > <>")
    op_bit = pp.oneOf("^ && || & |")

    operators = [
        (op_one, 1, pp.opAssoc.RIGHT),
        (op_sig, 2, pp.opAssoc.LEFT),
        (op_mul, 2, pp.opAssoc.LEFT),
        (op_cmp, 2, pp.opAssoc.LEFT),
        (op_bit, 2, pp.opAssoc.LEFT),
    ]
    reg = pp.Suppress("%") + pp.NotAny(pp.oneOf("hi lo")) + symbol
    hilo = pp.oneOf("%hi %lo") + pp.Suppress("(") + exp + pp.Suppress(")")
    exp << pp.infixNotation(term | reg | hilo, operators)

    adr = pp.Suppress("[") + exp + pp.Suppress("]")
    mem = adr  # +pp.Optional(symbol|imm)
    mem.setParseAction(lambda r: env.mem(r[0]))

    opd = exp | mem | reg
    opds = pp.Group(pp.delimitedList(opd))

    instr = mnemo + pp.Optional(opds) + pp.Optional(comment)

    @staticmethod
    def action_reg(toks):
        rname = toks[0]
        if rname.ref.startswith("asr"):
            return env.reg(rname.ref)
        return env.__dict__[rname.ref]

    @staticmethod
    def action_hilo(toks):
        v = toks[1]
        return env.hi(v) if toks[0] == "%hi" else env.lo(v).zeroextend(32)

    @staticmethod
    def action_exp(toks):
        tok = toks[0]
        if isinstance(tok, env.exp):
            return tok
        if len(tok) == 2:
            op = tok[0]
            r = tok[1]
            if isinstance(r, list):
                r = sparc_syntax.action_exp(r)
            return env.oper(op, r)
        elif len(tok) == 3:
            op = tok[1]
            l = tok[0]
            r = tok[2]
            if isinstance(l, list):
                l = sparc_syntax.action_exp(l)
            if isinstance(r, list):
                r = sparc_syntax.action_exp(r)
            return env.oper(op, l, r)
        else:
            return tok

    @staticmethod
    def action_instr(toks):
        i = instruction(b"")
        i.mnemonic = toks[0]
        if len(toks) > 1:
            i.operands = toks[1][0:]
        return asmhelper(i)

    # actions:
    reg.setParseAction(action_reg)
    hilo.setParseAction(action_hilo)
    exp.setParseAction(action_exp)
    instr.setParseAction(action_instr)


from amoco.cas.expressions import cst, op
from amoco.arch.sparc.spec_v8 import ISPECS
from amoco.arch.sparc.formats import CONDB, CONDT

spec_table = dict([(spec.iattr["mnemonic"], spec) for spec in ISPECS])
b_synonyms = {"b": "ba", "bgeu": "bcc", "blu": "bcs", "bz": "be", "bnz": "bne"}
t_synonyms = {"t": "ta", "tgeu": "tcc", "tlu": "tcs", "tz": "te", "tnz": "tne"}
b_cond = dict([(mn, cond) for cond, mn in CONDB.items()])
t_cond = dict([(mn, cond) for cond, mn in CONDT.items()])


def asmhelper(i):
    for idx, a in enumerate(i.operands):
        if a._is_mem:
            i.operands[idx] = a.a
    # Add implicit arguments
    if i.mnemonic in ["inc", "dec"] and len(i.operands) == 1:
        i.operands.insert(0, cst(1))
    # Expand reduced forms
    if i.mnemonic == "bset":
        i.mnemonic = "or"
        i.operands.insert(0, i.operands[1])
    elif i.mnemonic == "mov":
        i.mnemonic = "or"
        i.operands.insert(0, env.g0)
    elif i.mnemonic == "retl":
        i.mnemonic = "jmpl"
        i.operands.insert(0, op("+", env.o7, cst(8)))
        i.operands.insert(1, env.g0)
    elif i.mnemonic == "jmp":
        i.mnemonic = "jmpl"
        i.operands.insert(1, env.g0)
    elif i.mnemonic == "clr" and i.operands[0]._is_reg:
        i.mnemonic = "or"
        i.operands.insert(0, env.g0)
        i.operands.insert(0, env.g0)
    elif i.mnemonic == "clr":
        i.mnemonic = "st"
        i.operands.insert(0, env.g0)
    elif i.mnemonic == "inc":
        i.mnemonic = "add"
        i.operands.insert(0, i.operands[1])
    elif i.mnemonic == "dec":
        i.mnemonic = "sub"
        i.operands.insert(0, i.operands[1])
    elif i.mnemonic == "cmp":
        i.mnemonic = "subcc"
        i.operands.insert(2, env.g0)
    elif i.mnemonic == "btst":
        i.mnemonic = "andcc"
        i.operands.insert(2, env.g0)
        i.operands[0:2] = [i.operands[1], i.operands[0]]
    elif i.mnemonic == "nop":
        i.mnemonic = "sethi"
        i.operands = [cst(0, 22), env.g0]
    elif i.mnemonic == "restore" and len(i.operands) == 0:
        i.operands = [env.g0, env.g0, env.g0]
    # Branches and cc
    if i.mnemonic.endswith("cc") and i.mnemonic not in ["taddcc", "tsubcc", "mulscc"]:
        i.mnemonic = i.mnemonic[:-2]
        i.misc["icc"] = True
    if i.mnemonic.endswith(",a"):
        i.misc["annul"] = True
        i.mnemonic = i.mnemonic.rstrip(",a")
    if i.mnemonic in b_synonyms:
        i.mnemonic = b_synonyms[i.mnemonic]
    if i.mnemonic in b_cond:
        i.cond = b_cond[i.mnemonic]
        i.mnemonic = "b"
    if i.mnemonic in t_synonyms:
        i.mnemonic = t_synonyms[i.mnemonic]
    if i.mnemonic in t_cond:
        i.cond = t_cond[i.mnemonic]
        i.mnemonic = "t"
    if i.mnemonic == "call":
        if len(i.operands) > 1 and i.operands[1] != cst(0):
            raise ValueError("call has a non-zero second argument")
        i.operands = [i.operands[0]]
    # Additional internal tweaks
    if i.mnemonic == "sethi" and i.operands[0]._is_cst:
        i.operands[0].size = 22
    elif i.mnemonic == "std":
        i.rd = env.r.index(i.operands[0])
    elif i.mnemonic == "ldd":
        i.rd = env.r.index(i.operands[1])
    i.spec = spec_table[i.mnemonic]
    i.bytes = (0, 0, 0, 0)  # To have i.length == 4, for pc_npc emulation
    return i


# ----------------------------
# for testing:


def test_parser(cls):
    while 1:
        try:
            res = input("%s>" % cls.__name__)
            E = cls.instr.parseString(res, True)
            print(E)
        except pp.ParseException:
            logger.error("ParseException")
            return E
        except EOFError:
            return


if __name__ == "__main__":
    test_parser(sparc_syntax)
