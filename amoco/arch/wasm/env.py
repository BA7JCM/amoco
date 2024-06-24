# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2021 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

# import expressions:
from amoco.cas.expressions import reg, sym
from amoco.cas.expressions import is_reg_pc, is_reg_stack

from amoco.cas.expressions import *  # noqa: F403

# symbols from libgcc/unwind-dw2.c :
# -----------------------------------

WORD = 64

with is_reg_pc:
    op_ptr = reg("op_ptr", 64)

with is_reg_stack:
    sp = reg("sp", 64)

stack_elt = reg("stack_elt", 6)

registers = [op_ptr, sp, stack_elt]

i32 = sym("i32", 0x7F, 8)
i64 = sym("i64", 0x7E, 8)
f32 = sym("f32", 0x7D, 8)
f64 = sym("f64", 0x7C, 8)

numtype = {
    0x7F: i32,
    0x7E: i64,
    0x7D: f32,
    0x7C: f64,
}

funcref = sym("funcref", 0x70, 8)
externref = sym("externref", 0x6F, 8)

reftype = {
    0x70: funcref,
    0x6F: externref,
}

valtype = dict(numtype).update(reftype)

internals = {}
