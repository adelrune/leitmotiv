import music21
import random
from subprocess import run, check_output
import os
import sys
import m21_helpers
import re
import functools
from copy import deepcopy

artifact_folder = "tmp_artifacts"

# this is a fancy decorator that can act on the class of a method
class ltv_method:
    def __init__(self, fn):
        self.fn = fn

    def __set_name__(self, owning_class, name):
        # appends the function's name to the list of ltv methods
        owning_class.ltv_methods.append(name)
        @functools.wraps(self.fn)
        def wrapper(*args, **kwargs):
            # looks for the side_effect flag and deletes it from the passed arguments after saving its value
            side_effect = False
            if "side_effect" in kwargs:
                side_effect = kwargs["side_effect"]
                del(kwargs["side_effect"])
            # gets the value returned by the function
            method_self = args[0]
            value = self.fn(*args, **kwargs)
            # if the value is a music21 Stream, it means we must either modify the instance or create a new one
            if issubclass(type(value), music21.stream.Stream):
                # if the function was called with side-effects, modifies and returns the existing pattern, else make a new one
                if side_effect:
                    method_self.m21_repr = value
                    method_self.dirty_abc = True
                    return method_self
                else:
                    return Pattern(m21_repr=value, header=args[0].header_type)
            return value
        # overwrite with the wrapped function
        setattr(owning_class, name, wrapper)


class Reference:
    def __init__(self, identifier=None, value=None):
        self.identifier = identifier
        self.value = value
        self.origin_context = None
    def __repr__(self):
        return f"({self.identifier} -> {self.value})"
    def __eq__(self, other):
        return self.identifier == other.identifier and self.value == other.value


class LTVObject:
    ltv_methods = []
    def __init__(self):
        """builds the scope object of the methods accessible from leitmotiv"""
        self.scope = {method: getattr(self,method) for method in self.ltv_methods}

class LTVList(LTVObject):
    ltv_methods = []
    def __init__(self, items):
        self.items = items
        super().__init__()

    def __getitem__(self, key):
        return self.items[key]

    @ltv_method
    def append(self, el):
        self.items.append(Reference(value=el))

headers = {
    "normal": {"pre_header":"%%bgcolor white", "header":"\nX:1\nL:1/4\nK:C\n"},
    "perc1": {"pre_header":"""%%bgcolor white\n%%beginsvg\n<defs>\n<g id="xhead" class="stroke">\n<line y1="-2.5" y2="2.5" x1="-3.5" x2="3.5" style="stroke-width:0.75"></line>\n<line y1="-2.5" y2="2.5" x1="3.5" x2="-3.5" style="stroke-width:0.75"></line>\n</g>\n</defs>\n%%endsvg\n%%map shape key,C heads=xhead\n%%map shape key,E heads=xhead\n%%map shape key,F heads=xhead\n%%map shape key,G heads=xhead\n%%map shape key,A heads=xhead\n%%map shape key,B heads=xhead\n%%voicemap shape\n""","header":"X:1\nL:1/4\nK:C clef=perc stafflines=1\n"}
}

def list_index_of_instance(lst, el):
    for i in range(len(lst)):
        if lst[i] is el:
            return i
    raise Exception("instance not in list")

def lst_shift(seq, n=0):
    # thank you stackoverflow
    a = n % len(seq)
    return seq[-a:] + seq[:-a]

class Pattern(LTVObject):
    def __init__(self, abcstring=None, m21_repr=None, header="normal"):
        self.id = random.randrange(0,10000000)
        self.m21_repr = m21_repr
        self.dirty_abc = abcstring is None
        self.musicxml_s = None
        self.abcstring = abcstring
        self.header_type = header
        self.pre_header = headers[header]["pre_header"]
        self.header = headers[header]["header"]
        self.svgfile_s = None
        self.abcfile_s = None
        if self.abcstring is not None:
            self.write_abc_artifact()
        if self.m21_repr is None:
            # generates the abc file artifact
            # gets the music21 IR from the abc
            self.m21_repr = music21.converter.parse(self.get_abc2xml(), format="xml")
            self.update_abc()

        super().__init__()

    @ltv_method
    def shift(self, shift):
        """shift each part by <shift> notes or rests"""
        stream = self.m21_repr
        new_stream = music21.stream.Stream()
        for part in stream.parts:
            new_part = music21.stream.Part()
            elems_in_part = list(part.flat)
            notes_or_rests = m21_helpers.findByClass(part, ("Note","Rest"))
            notes_idxs = [list_index_of_instance(elems_in_part, n_o_r) for n_o_r in m21_helpers.findByClass(part, ("Note","Rest"))]
            shifted_notes = lst_shift(notes_or_rests, shift)
            current_note_or_rest = 0
            for i in range(len(elems_in_part)):
                elem = None
                if i not in notes_idxs:
                    elem = deepcopy(elems_in_part[i])
                else:
                    elem = deepcopy(shifted_notes[current_note_or_rest])
                    current_note_or_rest+=1
                new_part.append(elem)
            new_stream.append(new_part)

        return new_stream

    @ltv_method
    def count_notes(self):
        return max([len(m21_helpers.findByClass(p, ("Note", "Rest"))) for p in m21_helpers.getParts(self.m21_repr)])


    @ltv_method
    def transpose(self, interval, keep_keys=False):
        transposed = self.m21_repr.transpose(interval)

        if not keep_keys:
            inversed_interval = music21.interval.Interval(interval).reverse()
            for key in m21_helpers.findByClass(transposed, "Key"):
                key.transpose(inversed_interval, inPlace=True)
        return transposed

    @ltv_method
    def to_midi(self, filename):
        mf = music21.midi.translate.streamToMidiFile(self.m21_repr)
        mf.open(filename, 'wb')
        mf.write()
        mf.close()

    @ltv_method
    def to_xml(self, filename):
        self.m21_repr.write('musicxml', fp=filename)


    def write_abc_artifact(self):
        self.abcfile_s = f"{artifact_folder}/{self.id}.abc"
        open(self.abcfile_s,"w").write(self.pre_header+self.header+self.abcstring)


    def get_abc2xml(self):
        if self.abcfile_s is None:
            self.update_abc()
        abcfile_s = f"{artifact_folder}/{self.id}_noheader.abc"
        open(abcfile_s,"w").write(headers["normal"]["header"]+ self.abcstring)
        xml = check_output(["python", __file__.split("ltv_builtins.py")[0]+"abc2xml.py", f"{abcfile_s}"]).decode("utf-8")
        return xml

    def update_abc(self):
        xml_path = f"{artifact_folder}/{self.id}.xml"
        self.to_xml(xml_path)
        abc = check_output(["python", __file__.split("ltv_builtins.py")[0]+"xml2abc.py", "-d 4", f"{xml_path}"]).decode("utf-8")

        self.abcstring = "\n".join(filter(lambda line: not re.match("[A-Z]:.*", line), abc.split("\n")))
        self.write_abc_artifact()

    def generate_image(self):
        if self.svgfile_s is None or self.dirty_abc:
            self.update_abc()
        outfile_s = f"{artifact_folder}/{self.id}.svg"
        run(["abcm2ps", "-g", self.abcfile_s, "-O", outfile_s])
        # abcm2ps appends 001 to the filename...
        self.svgfile_s = f"{artifact_folder}/{self.id}001.svg"
        return self.svgfile_s


def concat(*args):
    """concatenate patterns on top of eachother"""
    if type(args[0]) == LTVList:
        args = [it.value for it in args[0].items]
    stream = music21.stream.Stream()
    parts = [music21.stream.Part() for i in range(max([len(m21_helpers.getParts(pattern.m21_repr)) for pattern in args]))]
    for p in parts:
        stream.append(p)
    for pattern in args:
        for i, part in enumerate(m21_helpers.getParts(pattern.m21_repr)):
            for thing in list(part):
                parts[i].append(deepcopy(thing))
    return Pattern(m21_repr=stream, header=args[0].header_type)

def stack(*args):
    """stack multiple patterns on top of eachother"""
    if type(args[0]) == LTVList:
        args = [it.value for it in args[0].items]
    stream = music21.stream.Stream()
    for pattern in args:
        part = music21.stream.Part()
        part.append(pattern.m21_repr)
        stream.append(part)

    return Pattern(m21_repr=stream, header=args[0].header_type)


global_scope = {"concat":concat, "stack":stack, "print":print}
