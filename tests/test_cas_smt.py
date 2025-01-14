import pytest
from amoco.config import conf
from amoco.cas.smt import has_solver, solver
from amoco.cas.expressions import reg, mem, slc, cst, complexity


@pytest.mark.skipif(not has_solver, reason="no smt solver loaded")
def test_reg_bv(x, y):
    clx = conf.Cas.complexity
    conf.Cas.complexity = 100
    xl = slc(x, 0, 8, ref="xl")
    xh = slc(x, 8, 8, ref="xh")
    z = (x ^ cst(0xCAFEBABE, 32)) + (y + (x >> 2))
    assert complexity(z) < 100
    m = solver([z == cst(0x0, 32), xl == 0xA, xh == 0x84]).get_model()
    assert m is not None
    xv = m.eval(x.to_smtlib()).as_long()
    yv = m.eval(y.to_smtlib()).as_long()
    assert m.eval(xl.to_smtlib()).as_long() == 0xA
    assert m.eval(xh.to_smtlib()).as_long() == 0x84
    assert ((xv ^ 0xCAFEBABE) + (yv + (xv >> 2))) & 0xFFFFFFFF == 0
    conf.Cas.complexity = clx


@pytest.mark.skipif(not has_solver, reason="no smt solver loaded")
def test_mem_bv():
    clx = conf.Cas.complexity
    conf.Cas.complexity = 100
    p = reg("p", 32)
    x = mem(p, 32)
    y = mem(p + 2, 32)
    yl = y[0:16]
    xh = x[16:32]
    z = (x ^ cst(0xCAFEBABE, 32)) + (y + (x >> 2))
    s = solver()
    m = s.get_mapper([z == cst(0, 32), p == 0x0804ABCD])
    assert m is not None
    assert m(xh) == m(yl)
    assert m(z) == 0
    conf.Cas.complexity = clx
