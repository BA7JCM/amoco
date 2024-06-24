# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2012 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license


class generation(dict):
    def lastdict(self):
        return self

    def __setitem__(self, k, v):
        self.hist = (k, self.get(k, k))
        return super().__setitem__(k, v)

    def __getitem__(self, k):
        return self.get(k, None)

    def cleanup(self):
        K = [k for k in self if k._is_reg]
        for k in K:
            del self[k]


class nextgeneration(object):
    def __init__(self, *args, **kargs):
        self.od = dict(*args, **kargs)

    def __getall(self, k):
        return self.od.get(k, [])

    def __setitem__(self, k, v):
        oldv = self.__getall(k)
        oldv.append(v)
        self.od[k] = oldv

    def __getitem__(self, k):
        v = self.__getall(k)
        try:
            return v[-1]
        except IndexError:
            return None

    def get(self, k, default):
        r = self[k]
        if r is None:
            r = default
        return r

    def keygen(self, k, g):
        v = self.__getall(k)
        return v[g]

    # order at generation g is conserved;
    def getgen(self, g):
        d = nextgeneration()
        for k in self.od:
            d[k] = self.keygen(k, g)
        return d

    def lastdict(self):
        d = dict()
        for k in self.od:
            d[k] = self[k]
        return d
