from amoco.ui import render
from amoco.ui.graphics.rich_ import rtrow


def test_vltable():
    T = render.vltable(formatter="Null")
    T.addrow(
        [
            (render.Token.Literal, "abcd"),
            (render.Token.Register, "eax"),
            (render.Token.Column, "<-"),
            (render.Token.Constant, "0x23"),
        ]
    )
    T.addrow(
        [
            (render.Token.Literal, "abcd"),
            (render.Token.Register, "ebx"),
            (render.Token.Column, "<-"),
            (render.Token.Mnemonic, "mov"),
        ]
    )
    T.addrow(
        [
            (render.Token.Literal, "abcdxxxxxxx"),
            (render.Token.Register, "eflags"),
            (render.Token.Column, "<-"),
            (render.Token.Memory, "M32(eax+1)"),
        ]
    )
    assert T.nrows == 3
    assert T.ncols == 2
    assert T.colsize[0] == 17
    assert T.getcolsize(0) == 17
    T.hiderow(2)
    assert T.getcolsize(0) == 7
    T.showrow(2)
    T.grep("eax", invert=True)
    assert T.hidden_r.issuperset((0, 2))
    c0 = T.getcolsize(0)
    assert c0 == 7
    T.setcolsize(0, c0)
    T.squash_r = True
    T.squash_c = True
    R = sum((rtrow(r) for r in T.rows),[])
    assert R[2] == '[literal]abcd[/][register]ebx[/]'
