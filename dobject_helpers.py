"""
Copyright 2008 Benjamin M. Schwartz

This file is LGPLv2+.  This file, dobject_helpers.py, is part of DObject.

DObject is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

DObject is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with DObject.  If not, see <http://www.gnu.org/licenses/>.
"""

import bisect

"""
dobject_helpers is a collection of functions and data structures that are useful
to DObject, but are not specific to DBus or networked applications.
"""

def merge(a, b, l=True, g=True, e=True):
    """Internal helper function for combining sets represented as sorted lists"""
    x = 0
    X = len(a)
    if X == 0:
        if g:
            return list(b)
        else:
            return []
    y = 0
    Y = len(b)
    if Y == 0:
        if l:
            return list(a)
        else:
            return []
    out = []
    p = a[x]
    q = b[y]
    while x < X and y < Y:
        if p < q:
            if l: out.append(p)
            x += 1
            if x < X: p = a[x]
        elif p > q:
            if g: out.append(q)
            y += 1
            if y < Y: q = b[y]
        else:
            if e: out.append(p)
            x += 1
            if x < X: p = a[x]
            y += 1
            if y < Y: q = b[y]       
    if x < X:
        if l: out.extend(a[x:])
    else:
        if g: out.extend(b[y:])
    return out

def merge_or(a,b):
    return merge(a,b, True, True, True)

def merge_xor(a,b):
    return merge(a, b, True, True, False)

def merge_and(a,b):
    return merge(a, b, False, False, True)

def merge_sub(a,b):
    return merge(a, b, True, False, False)

def kill_dupes(a): #assumes a is sorted
    """Internal helper function for removing duplicates in a sorted list"""
    prev = a[0]
    out = [prev]
    for i in range(1, len(a)):
        item = a[i]
        if item != prev:
            out.append(item)
            prev = item
    return out

class Comparable:
    """Currently, ListSet does not provide a mechanism for specifying a
    comparator.  Users who would like to specify a comparator other than the one
    native to the item may do so by wrapping the item in a Comparable.
    """
    def __init__(self, item, comparator):
        self.item = item
        self._cmp = comparator
    
    def __cmp__(self, other):
        return self._cmp(self.item, other)



