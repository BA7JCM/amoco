from amoco.cas.mapper import mapper
from amoco.arch.x64.cpu_x64 import cpu


def test_mapper_000():
    # create two instructions
    # movq    %rcx, (%rip)
    # movq    (%rip), %rcx
    i0 = cpu.disassemble(b"\x48\x89\x0d\x00\x00\x00\x00")
    i1 = cpu.disassemble(b"\x48\x8b\x0d\x00\x00\x00\x00")
    # modify the first instruction to insert a label, e.g. because
    # there is a relocation
    # movq    %rcx, foo(%rip)
    i0.operands[0].a.disp = cpu.lab("foo", size=64)
    # evaluate those two instructions
    m = mapper()
    i0(m)
    i1(m)
    assert str(m[cpu.rcx]) == "M64(rip+14)"
