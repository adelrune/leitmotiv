def findByClass(stream, classlist):
    if type(classlist) not in {tuple, list}:
        classlist = (classlist,)
    return list(filter(lambda el: el.isClassOrSubclass(classlist), stream.flat))
