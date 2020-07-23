import music21
import random
from subprocess import run, check_output
import os
import sys
import m21_helpers
import re
import functools

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
                    return Pattern(m21_repr=value)
            return value
        # overwrite with the wrapped function
        setattr(owning_class, name, wrapper)

class LtvObject:
    ltv_methods = []
    def __init__(self):
        """builds the scope object of the methods accessible from leitmotiv"""
        self.scope = {method: getattr(self,method) for method in self.ltv_methods}

class ABCHeader(LtvObject):
    def __init__(self):
        self.X = 1
        self.L = "1/4"
        self.K = "C"
        super().__init__()

class Pattern(LtvObject):
    def __init__(self, abcstring=None, m21_repr=None):
        self.id = random.randrange(0,10000000)
        self.m21_repr = m21_repr
        self.dirty_abc = abcstring is None
        self.musicxml_s = None
        self.abcstring = abcstring
        self.header = "%%bgcolor white\nX:1\nL:1/4\nK:C\n"
        self.svgfile_s = None
        self.abcfile_s = f"{artifact_folder}/{self.id}.abc"
        if self.m21_repr is None:
            # generates the abc file artifact
            self.write_abc_artifact()
            # gets the music21 IR from the abc
            self.m21_repr = music21.converter.parse(self.abcfile_s)

        super().__init__()

    @ltv_method
    def shift(self, shift):
        pass

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
        open(self.abcfile_s,"w").write(self.header+self.abcstring)



    def update_abc(self):
        xml_path = f"{artifact_folder}/{self.id}.xml"
        self.to_xml(xml_path)
        print(__file__)
        abc = check_output(["python", __file__.split("ltv_builtins.py")[0]+"xml2abc.py", f"{xml_path}"]).decode("utf-8")
        self.abcstring = header_stripped_abc = "\n".join(filter(lambda line: not re.match("[A-Z]:.*", line), abc.split("\n")))
        self.write_abc_artifact()

    def generate_image(self):

        if self.svgfile_s is None or self.dirty_abc:

            if self.dirty_abc:
                self.update_abc()

            outfile_s = f"{artifact_folder}/{self.id}.svg"
            run(["abcm2ps", "-g", self.abcfile_s, "-O", outfile_s])
            # abcm2ps appends 001 to the filename...
            self.svgfile_s = f"{artifact_folder}/{self.id}001.svg"
            return self.svgfile_s


def concat(*args):
    """concatenate patterns on top of eachother"""
    stream = music21.stream.Stream()
    for pattern in args:
        stream.append(pattern.m21_repr)
    return Pattern(m21_repr=stream)

def stack(*args):
    """stack multiple patterns on top of eachother"""
    stream = music21.stream.Stream()
    for pattern in args:
        part = music21.stream.Part()
        part.append(pattern.m21_repr)
        stream.append(part)

    return Pattern(m21_repr=stream)


global_scope = {"concat":concat, "stack":stack, "print":print}
