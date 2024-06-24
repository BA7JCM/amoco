# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2016 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

import struct

from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")

from .core import StructCore, Alltypes
from .utils import read_leb128, write_uleb128, write_sleb128

# ------------------------------------------------------------------------------


class Field(object):
    """
    A Field object defines an element of a structure class, associating a name
    to a structure type and a count. A count of 0 means that the element
    is an object of type typename, a count>0 means that the element is a list
    of objects of type typename of length count.

    Attributes:
        typename (str) : name of a Structure type for this field.
        count (int=0)  : A count of 0 means that the element
            is an object of type typename, a count>0 means that the element is a list
            of length count of objects of type typename
        name (str)     : the name associated to this field.
        type (StructCore) : getter for the type associated with the field's typename.
        comment (str) : comment, useful for pretty printing field usage
        order (str) : forces the endianness of this field.

    Methods:
        size () : number of bytes eaten by this field.
        format (): format string that allows to struct.(un)pack the field as a
                       string of bytes.
        unpack (data,offset=0) : unpacks a data from given offset using
            the field internal byte ordering. Returns the object (if count is 0) or the
            list of objects of type typename.
        get (data,offset=0) : returns the field name and the unpacked value
            for this field.
        pack (value) : packs the value with the internal order and returns the
            byte string according to type typename.
    """

    def __init__(self, ftype, fcount=0, fname=None, forder=None, falign=1, fcomment=""):
        self.__type = None
        if isinstance(ftype, type):
            self.__type = ftype
            self.typename = ftype.__name__
        else:
            self.typename = ftype
        self.count = fcount
        self.name = fname
        self.order = forder or "<"
        self._align_value = falign
        self.comment = fcomment
        self.instance = None

    @property
    def type(self):
        if self.__type is None:
            try:
                cls = Alltypes[self.typename]
            except KeyError:
                logger.warning("type %s is not defined" % self.typename)
            else:
                self.__type = cls
        return self.__type

    def format(self, psize=0):
        """
        The format of a regular Field (ie. not derived from RawField) is always returned
        as matching a finite-length string.
        """
        sz = self.size()
        return "%ds" % sz

    def size(self, psize=0):
        # if the field belongs to an instance and was unpacked already,
        # we return the actual byte-length of the resulting struct:
        try:
            return len(self.instance[self.name])
        except Exception:
            pass
        # otherwise we return the natural size of the field's type,
        # which may be infinite if the type contains a VarField...
        try:
            sz = self.type.size(psize)
        except AttributeError:
            return float("Infinity")
        else:
            if self.count > 0:
                sz = sz * self.count
            return sz

    @property
    def source(self):
        res = "%s" % self.typename
        if self.count > 0:
            res += "*%d" % self.count
        res += ": %s" % self.name
        if self.comment:
            res += " ;%s" % self.comment
        return res

    def __len__(self):
        return self.size()

    def __eq__(self, other):
        if (
            (self.typename == other.typename)
            and (self.count == other.count)
            and (self.order == other.order)
            and (self._align_value == other._align_value)
        ):
            return True
        else:
            return False

    def align_value(self, psize=0):
        if self._align_value:
            return self._align_value
        if self.type:
            return self.type.align_value(psize)
        return psize

    def align(self, offset, psize=0):
        A = self.align_value(psize)
        if A == 0:
            return offset
        r = offset % A
        if r == 0:
            return offset
        return offset + (A - r)

    def unpack(self, data, offset=0, psize=0):
        "returns a (sequence of count) element(s) of its self.type"
        blob = self.type().unpack(data, offset, psize)
        if self.count > 0:
            # since we are not a RawField, blob is normally a StructCore instance,
            # but it can be a python raw type in case self is a typedef.
            # Thus, we need to declare a 'sizeof' operator to correctly compute
            # the size of each unpacked blob:
            if isinstance(blob, (bytes, StructCore)):
                sizeof = lambda b: len(b)
            else:
                sz = self.type.size(psize)
                if sz < float("Infinity"):
                    sizeof = lambda b: sz
                else:
                    sizeof = lambda b: sum((x.size(psize) for x in b), 0)
            # now lets unpack the rest of the series:
            sz = sizeof(blob)
            count = self.count
            blob = [blob]
            count -= 1
            offset += sz
            while count > 0:
                nextblob = self.type().unpack(data, offset, psize)
                blob.append(nextblob)
                offset += sizeof(nextblob)
                count -= 1
        return blob

    def get(self, data, offset=0, psize=0):
        return (self.name, self.unpack(data, offset, psize))

    def pack(self, value, psize=0):
        if self.count > 0:
            return b"".join([self.type().pack(v, psize) for v in value])
        return self.type.pack(value, psize)

    def copy(self, obj=None):
        cls = self.__class__
        newf = cls(
            self.typename,
            self.count,
            self.name,
            self.order,
            self._align_value,
            self.comment,
        )
        newf.instance = obj
        return newf

    def __call__(self):
        return self.copy()

    def __repr__(self):
        try:
            fmt = self.type.format()
        except (AttributeError, KeyError):
            fmt = "?"
        r = "<Field %s {%s}" % (self.name, fmt)
        if self.count > 0:
            r += "*%d" % self.count
        r += " (%s)>" % self.comment if self.comment else ">"
        return r


# ------------------------------------------------------------------------------


class RawField(Field):
    """
    A RawField is a Field associated to a *raw* type, i.e. an internal type
    matching a standard C type (u)int8/16/32/64, floats/double, (u)char.
    Contrarily to a generic Field which essentially forward the unpack call to
    its subtype, a RawField relies on the struct package to return the raw
    unpacked value.
    """

    @property
    def type(self):
        return None

    def format(self, psize=0):
        fmt = self.typename
        if self.count == 0:
            return fmt
        sz = self.count
        return "%d%s" % (sz, fmt)

    def align_value(self, psize=0):
        tn = self.typename
        if psize and (tn in ("P", "L", "l")):
            tn = {4: "I", 8: "Q", 32: "I", 64: "Q"}.get(psize, tn)
        sz = struct.calcsize(tn)
        return sz

    def size(self, psize=0):
        sz = self.align_value(psize)
        if self.count > 0:
            sz = sz * self.count
        return sz

    def unpack(self, data, offset=0, psize=0):
        pfx = "%d" % self.count if self.count > 0 else ""
        tn = self.typename
        if psize and tn in ("P", "L", "l"):
            tn = {4: "I", 8: "Q", 32: "I", 64: "Q"}.get(psize, tn)
        res = struct.unpack(
            self.order + pfx + tn, data[offset : offset + self.size(psize)]
        )
        if self.count == 0 or tn == "s":
            return res[0]
        if tn == "c":
            return b"".join(res)
        return res

    def pack(self, value, psize=0):
        fmt = self.typename
        if psize and fmt in ("P", "L", "l"):
            fmt = {4: "I", 8: "Q", 32: "I", 64: "Q"}.get(psize, fmt)
        pfx = "%d" % self.count if self.count > 0 else ""
        order = self.ORDER if hasattr(self, "ORDER") else self.order
        if fmt == "c" and isinstance(value, bytes):
            fmt = "s"
        res = struct.pack(order + pfx + fmt, value)
        return res

    def __repr__(self):
        fmt = self.typename
        r = "<Field %s [%s]" % (self.name, fmt)
        if self.count > 0:
            r += "*%d" % self.count
        r += " (%s)>" % self.comment if self.comment else ">"
        return r


# ------------------------------------------------------------------------------


class BitField(RawField):
    """
    A BitField is a 0-count RawField with additional subnames and subsizes to allow
    unpack the type into several named values each of given bit sizes.

    Note that The order of subfields in a BitField **always** goes from LSB to MSB.
    Subfields are unpacked once the BitField type has been unpacked according to
    its own endianness indicator.

    Arguments:
        - The ftype argument is the one that gets "splitted" into parts of bits.
        - The fcount argument is a list that defines the size of each splitted part
          from least to most significant bit.
        - The fname argument is a list that defines the name of each splitted part
          according to fcount.
        - the forder argument indicates the byte ordering (not the bit ordering.)
    """

    def __init__(self, ftype, fcount=0, fname=None, forder=None, falign=1, fcomment=""):
        super().__init__(ftype, 0, "", forder, falign, fcomment)
        self.subsizes = fcount or []
        # names of each splitted part is provided here:
        self.subnames = fname or []
        # other attributes are as usual...

    def unpack(self, data, offset=0, psize=0):
        value = super().unpack(data, offset)
        D = {}
        l = 0
        for name, sz in zip(self.subnames, self.subsizes):
            mask = (1 << sz) - 1
            D[name] = (value >> l) & mask
            l += sz
        return D

    def pack(self, D, psize=0):
        value = 0
        l = 0
        for x, sz in zip(self.subnames, self.subsizes):
            mask = (1 << sz) - 1
            v = (D[x] & mask) << l
            value |= v
            l += sz
        return super().pack(value, psize)

    def copy(self, obj=None):
        cls = self.__class__
        newf = cls(
            self.typename,
            self.subsizes,
            self.subnames,
            self.order,
            self._align_value,
            self.comment,
        )
        newf.instance = obj
        return newf

    def concat(self, other):
        oss = other.subsizes[:]
        osn = other.subnames[:]
        while oss and (self.size() * 8 >= sum(self.subsizes, oss[0])):
            self.subsizes.append(oss.pop(0))
            if osn:
                self.subnames.append(osn.pop(0))
        if oss or osn:
            logger.debug("BitField size too small in %s" % self)
            raise TypeError

    def __repr__(self):
        pre = " " * 7
        f = [pre + "%s:%s" % (n, s) for n, s in zip(self.subnames, self.subsizes)]
        s = "\n".join(f).strip()
        return "<Field %s>" % s


class BitFieldEx(Field):
    """
    A BitFieldEx is identical to a BitField but inherits from Field rather than RawField.
    This allows to rely on a type that has been defined from a macro or a typedef.
    """

    def __init__(self, ftype, fcount=0, fname=None, forder=None, falign=1, fcomment=""):
        super().__init__(ftype, 0, "", forder, falign, fcomment)
        self.subsizes = fcount or []
        # names of each splitted part is provided here:
        self.subnames = fname or []
        # other attributes are as usual...

    def unpack(self, data, offset=0, psize=0):
        value = super().unpack(data, offset)
        D = {}
        l = 0
        for name, sz in zip(self.subnames, self.subsizes):
            mask = (1 << sz) - 1
            D[name] = (value >> l) & mask
            l += sz
        return D

    def pack(self, D, psize=0):
        value = 0
        l = 0
        for x, sz in zip(self.subnames, self.subsizes):
            mask = (1 << sz) - 1
            v = (D[x] & mask) << l
            value |= v
            l += sz
        return super().pack(value, psize)

    def copy(self, obj=None):
        cls = self.__class__
        newf = cls(
            self.typename,
            self.subsizes,
            self.subnames,
            self.order,
            self._align_value,
            self.comment,
        )
        newf.instance = obj
        return newf

    def __repr__(self):
        r = "<Field %s>" % str(
            ["%s:%s" % (n, s) for n, s in zip(self.subnames, self.subsizes)]
        )
        return r


# ------------------------------------------------------------------------------


class VarField(RawField):
    """
    A VarField is a RawField with variable length, associated with a
    termination condition (a function) that will end the unpack method.
    An instance of VarField has an infinite size() unless it has been
    unpacked with data.

    The default terminate condition is to match the null byte.
    """

    def format(self, psize=0):
        fmt = self.typename
        cnt = self.count if hasattr(self, "_sz") else "#"
        return "%s%s" % (cnt, fmt)

    def size(self, psize=0):
        try:
            return self._sz
        except AttributeError:
            return float("Infinity")

    def unpack(self, data, offset=0, psize=0):
        tn = self.typename
        if psize and tn == "P":
            tn = {4: "I", 8: "Q", 32: "I", 64: "Q"}.get(psize, "P")
        sz1 = struct.calcsize(tn)
        el1 = data[offset : offset + sz1]
        el1 = struct.unpack(self.order + self.typename, el1)[0]
        res = [el1]
        pos = offset + sz1
        while not self.terminate(el1, field=self):
            el1 = data[pos : pos + sz1]
            el1 = struct.unpack(self.order + self.typename, el1)[0]
            res.append(el1)
            pos += sz1
            self._sz = pos - offset
            self.count = len(res)
        if self.typename == "s":
            return b"".join(res)
        if self.typename == "c":
            return b"".join(res)
        return res

    def pack(self, value, psize=0):
        tn = self.typename
        if psize and tn == "P":
            tn = {4: "I", 8: "Q", 32: "I", 64: "Q"}.get(psize, "P")
        res = [struct.pack(self.order + tn, v) for v in value]
        return b"".join(res)

    def copy(self, obj=None):
        newf = super().copy(obj)
        if hasattr(self, "_terminate"):
            newf._terminate = self._terminate
        return newf

    def __repr__(self):
        r = "<VarField %s [%s]" % (self.name, self.format())
        r += " (%s)>" % self.comment if self.comment else ">"
        return r

    @staticmethod
    def __default_terminate(val, field=None):
        if isinstance(val, bytes):
            return val == b"\0"
        else:
            return val == 0

    def terminate(self, val, field=None):
        if hasattr(self, "_terminate"):
            f = self._terminate
            return f(val, field)
        return self.__default_terminate(val, field)

    def set_terminate(self, func):
        self._terminate = func


# ------------------------------------------------------------------------------


class Leb128Field(VarField):
    """
    A Leb128Field is a VarField associated with a
    termination condition that decodes LEB128 integers.
    """

    def __init__(self, ftype, fcount=0, fname=None, forder=None, falign=1, fcomment=""):
        super().__init__(ftype, fcount, fname, forder, falign, fcomment)
        self.__type = None
        self.typename = "c"
        self.sign = -1 if ftype in "bhil" else 1
        self.N = struct.calcsize(ftype)
        self.type_private = False
        self.count = 0
        self.name = fname
        self.order = "<"
        self._align_value = falign
        self.comment = fcomment
        self._sz = None
        self.instance = None

    def format(self, psize=0):
        if self._sz is None:
            return "#c"
        else:
            return "%dc" % self._sz

    def _terminate(self, b, f):
        return b & 0x80 == 0

    def unpack(self, data, offset=0, psize=0):
        val, sz = read_leb128(data, self.sign, offset)
        self._sz = sz
        return val

    def pack(self, value, psize=0):
        if self.sign == 1:
            return write_uleb128(value)
        else:
            return write_sleb128(value)


# ------------------------------------------------------------------------------


class CntField(RawField):
    """
    A CntField is a RawField where the amount of elements to unpack
    is provided as first bytes, encoded as either a byte/word/dword.

    A CntField has infinite size until its format is legit, ie. it has
    unpacked some data and thus decoded the actual count of elements
    that define its value."
    """

    def format(self, psize=0):
        fmt = self.typename
        if psize and fmt == "P":
            fmt = {4: "I", 8: "Q", 32: "I", 64: "Q"}.get(psize, "P")
        # fcount is used as a placeholder for the initial fcount value
        # that correspond to the formatting of the counter. For example
        # for a CntField defined from s*~I, the typename is 's' and the
        # count is initially set to '~I' to indicate that the counter is
        # to be decoded as an uint32 from first 4 bytes.
        if hasattr(self, "fcount"):
            cnt = "%s" % self.fcount[1:]
            if self.count == 0:
                return cnt
            else:
                cnt += "%d" % self.count
        else:
            cnt = "#"
        return "%s%s" % (cnt, fmt)

    def size(self, psize=0):
        try:
            return struct.calcsize(self.format(psize))
        except Exception:
            return float("Infinity")

    def unpack(self, data, offset=0, psize=0):
        if hasattr(self, "fcount"):
            # the structure has been unpacked already, lets restore
            # the count to its initial form.
            self.count = self.fcount
        # decode the actual count:
        sz = struct.calcsize(self.count[1:])  # (skip '~')
        nb = data[offset : offset + sz]
        nb = struct.unpack(self.order + self.count[1:], nb)[0]
        # save the initial count form
        self.fcount = self.count
        # ...before overwritting with actual value:
        self.count = nb
        if self.count == 0:
            res = [0, b""]
        else:
            # now fully unpack the whole field:
            res = struct.unpack(
                self.order + self.format(psize),
                data[offset : offset + self.size(psize)],
            )
        if self.typename == "s":
            return res[1]
        if self.typename == "c":
            return b"".join(res[1:])
        if self.count == 0:
            return None
        return res[1:]

    def pack(self, value, psize=0):
        if not hasattr(self, "fcount"):
            self.fcount = self.count
        self.count = len(value)
        if isinstance(value, list):
            res = struct.pack(self.order + self.format(psize), self.count, *value)
        else:
            res = struct.pack(self.order + self.format(psize), self.count, value)
        return res

    def __repr__(self):
        fmt = self.format()
        r = "<Field %s [%s]" % (self.name, fmt)
        r += " (%s)>" % self.comment if self.comment else ">"
        return r


# ------------------------------------------------------------------------------


class BindedField(CntField):
    """
    A BindField is a CntField where the counter is provided
    by a (previously unpacked) field of the same structure.
    """

    def format(self, psize=0):
        fmt = self.typename
        if psize and fmt == "P":
            fmt = {4: "I", 8: "Q", 32: "I", 64: "Q"}.get(psize, "P")
        if hasattr(self, "fcount"):
            cnt = self.count
        else:
            cnt = "#"
        if self.count == 0:
            return ""
        return "%s%s" % (cnt, fmt)

    def size(self, psize=0):
        try:
            return struct.calcsize(self.format(psize))
        except Exception:
            return float("Infinity")

    def unpack(self, data, offset=0, psize=0):
        if hasattr(self, "fcount"):
            self.count = self.fcount
        self.fcount = self.count
        boundname = self.count[1:]
        self.count = self.instance[boundname]
        if self.count == 0:
            return None
        res = struct.unpack(
            self.order + self.format(psize), data[offset : offset + self.size(psize)]
        )
        if self.typename == "s":
            return res[0]
        return res
