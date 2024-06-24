# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2014 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

# import expressions:
from amoco.cas.expressions import reg, slc, ext
from amoco.cas.expressions import is_reg_flags, is_reg_pc, is_reg_stack

from amoco.cas.expressions import *  # noqa: F403

# registers :
# -----------

# main reg set:
R = [reg("R%d" % r, 8) for r in range(32)]

X = reg("X", 16)
R[26] = slc(X, 0, 8, "XL")
R[27] = slc(X, 8, 8, "XH")
Y = reg("Y", 16)
R[28] = slc(Y, 0, 8, "YL")
R[29] = slc(Y, 8, 8, "YH")
Z = reg("Z", 16)
R[30] = slc(Z, 0, 8, "ZL")
R[31] = slc(Z, 8, 8, "ZH")

with is_reg_flags:
    SREG = reg("SREG", 8)
    cf = slc(SREG, 0, 1, "C")  # Carry
    zf = slc(SREG, 1, 1, "Z")  # Zero
    nf = slc(SREG, 2, 1, "N")  # Negative
    vf = slc(SREG, 3, 1, "V")  # Overflow
    sf = slc(SREG, 4, 1, "S")  # N^V (sign test)
    hf = slc(SREG, 5, 1, "H")  # Half-carry
    tf = slc(SREG, 6, 1, "T")  # Transfer
    i_ = slc(SREG, 7, 1, "I")  # Global Interrupt

with is_reg_pc:
    pc = reg("PC", 16)

with is_reg_stack:
    sp = reg("SP", 16)
    spl = slc(sp, 0, 8, "SPL")
    sph = slc(sp, 8, 8, "SPH")

RAMPX = reg("RAMPX", 8)
RAMPY = reg("RAMPY", 8)
RAMPZ = reg("RAMPZ", 8)
RAMPD = reg("RAMPD", 8)
EIND = reg("EIND", 8)

registers = R + [sp, pc, SREG]

mmregs = {
    0x1E: reg("GPIOR0", 8),  # General Purpose I/O Register 0
    0x1F: reg(
        "EECR", 8
    ),  # EEPROM control register:[EERE, EEPE, EEMPE, EERIE, EEPM0, EEPM1, -, -]
    0x20: reg("EEDR", 8),  # data readout from the EEPROM @ EEAR
    0x21: reg("EEARL", 8),  # EEPROM address (Low)
    0x22: reg("EEARH", 8),  # EEPROM address (High)
    0x2A: reg("GPIOR1", 8),  # General Purpose I/O Register 1
    0x2B: reg("GPIOR2", 8),  # General Purpose I/O Register 2
    0x2C: reg("SPCR", 8),
    0x2D: reg("SPSR", 8),
    0x2E: reg("SPDR", 8),
    0x33: reg("SMCR", 8),  # Spleep Mode Control Register
    0x35: reg("MCUSR", 8),  # MCU Control Register
    0x3D: spl,
    0x3E: sph,
    0x3F: SREG,
    0x61: reg("CLKPR", 8),  # Clock Prescale
    0x64: reg("PRR", 8),  # Power Reduction
    0x66: reg("OSCCAL", 8),  # Oscillator Calibration
    0xC6: reg("UDR0", 8),
}

EECR = mmregs[0x1F]
EERE = slc(EECR, 0, 1, "EERE")  # EEPROM Read Enable
EEPE = slc(EECR, 1, 1, "EEPE")  # EEPROM Write Enable
EEMPE = slc(EECR, 2, 1, "EEMPE")  # EEPROM Master Write Enable
EERIE = slc(EECR, 3, 1, "EERIE")  # enable EEPROM ready interrupt
EEPM0 = slc(EECR, 4, 1, "EEPM0")  # EEPROM programming mode: 00=EraseWrite 01:EraseOnly
EEPM1 = slc(EECR, 5, 1, "EEPM1")  #                          10=WriteOnly  11:Reserved

vectors = [
    ext("RESET", size=8),
    ext("INT0", size=8),
    ext("INT1", size=8),
    ext("PCINT0", size=8),
    ext("PCINT1", size=8),
    ext("PCINT2", size=8),
    ext("WDT", size=8),
    ext("TIMER2_COMPA", size=8),
    ext("TIMER2_COMPB", size=8),
    ext("TIMER2_OVF", size=8),
    ext("TIMER1_CAPT", size=8),
    ext("TIMER1_COMPA", size=8),
    ext("TIMER1_COMPB", size=8),
    ext("TIMER1_OVF", size=8),
    ext("TIMER0_COMPA", size=8),
    ext("TIMER0_COMPB", size=8),
    ext("TIMER0_OVF", size=8),
    ext("SPI_STC", size=8),
    ext("USART_RX", size=8),
    ext("USART_UDRE", size=8),
    ext("USART_TX", size=8),
    ext("ADC", size=8),
    ext("EE_READY", size=8),
    ext("ANALOG_COMP", size=8),
    ext("TWI", size=8),
    ext("SPM_READY", size=8),
]

internals = {}
