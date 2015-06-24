#!/usr/bin/python
# https://github.com/owlbreeze/archive_compare
''' This util compares 2 tar archives and outputs the list of differences on stderr.
    If an output file is provided, it will also create an archive containing any changed
    files
'''
import sys, getopt
import tarfile
import hashlib
import os.path
import re


def genHash(tarFileObj):
    h = hashlib.sha1()
    while True:
        block = tarFileObj.read(10240)
        if not block:
            break
        h.update(block)
    tarFileObj.seek(0)
    return h.hexdigest()

class TarInfo():
    def __init__(self, tarinfo, fileobj=None):
        self.tarinfo = tarinfo
        if fileobj:
            self.sha1sum = genHash(fileobj)
        self.fileobj = fileobj

    # compare with another TarInfo
    def different(self, tarinfo):
        return tarinfo.name() != self.name() or \
                tarinfo.filetype() != self.filetype() or \
                tarinfo.size() != self.size() or \
                (tarinfo.issym() and (tarinfo.linkname() != self.linkname())) or \
                (tarinfo.isreg() and (tarinfo.sha1() != self.sha1()))

    def name(self):
        return self.tarinfo.name
    def sha1(self):
        return self.sha1sum
    def filetype(self):
        return self.tarinfo.type
    def size(self):
        return self.tarinfo.size
    def linkname(self):
        return self.tarinfo.linkname
    def isdir(self):
        return self.tarinfo.isdir()
    def issym(self):
        return self.tarinfo.issym()
    def isreg(self):
        return self.tarinfo.isreg() and not self.tarinfo.issym()
    def filetypestr(self):
        return \
            'slnk' if self.tarinfo.issym() else \
            'hlnk' if self.tarinfo.islnk() else \
            'dev' if self.tarinfo.isdev() else \
            'fifo' if self.tarinfo.isfifo() else \
            'dir' if self.tarinfo.isdir() else \
            'file' if self.tarinfo.isreg() else \
            'unkn'


def buildTarInfoList(tar):
    L = []
    for tarinfo in tar:
        if tarinfo.isreg() and not(tarinfo.issym()):
            L.append(TarInfo(tarinfo, tar.extractfile(tarinfo)))
        elif tarinfo.islnk():
            L.append(TarInfo(tarinfo, tar.extractfile(tarinfo)))
        else:
            L.append(TarInfo(tarinfo))
    return L

def filterModified(tarinfo, tarinfoList):
    name = tarinfo.name()
    for i in tarinfoList:
        if name == i.name():
            if tarinfo.different(i):
                return True
            else:
                break
    else: # not found
        return True
    return False

def filterRemoved(tarinfo, tarinfoList):
    name = tarinfo.name()
    for n in tarinfoList:
        if name == n.name():
            return False
    return True

def printUsage():
    print 'archive_compare.py -p <previousfile.tar.?z> -n <newfile.tar.?z> [-o <outputfile.tar.?z>]'
    print 'Note: list of modified & removed files will be printed on stderr'

def main(argv):
    prevfile = ''
    newfile = ''
    outputfile = ''
    try:
        opts, args = getopt.getopt(argv, "p:n:o:h", ["prev=", "new=", "output="])
    except getopt.GetoptError:
        printUsage()
        sys.exit(2)
        
    for opt, arg in opts:
        if opt == '-h':
            print 'archive_compare.py -p <previousfile> -n <newfile> -o <outputfile>'
            sys.exit()
        elif opt in ("-p", "--prev"):
            prevfile = arg
        elif opt in ("-n", "--new"):
            newfile = arg
        elif opt in ("-o", "--output"):
            outputfile = arg

    if not (newfile):
        print '  Missing command line option'
        printUsage()
        sys.exit()
        
    print '  Prevous file: ', prevfile
    print '  New file:     ', newfile
    print '  Output file:  ', outputfile

    # get members sorted of both files. any currently notable differences add to out list
    print '  opening %s...' % newfile
    newTar = tarfile.open(newfile, 'r:*')
    oldTar = None
    if prevfile:
        print '  opening %s...' % prevfile
        oldTar = tarfile.open(prevfile, 'r:*')

    print '  building listNew...',
    listNew = buildTarInfoList(newTar)
    print '  done (%d files)' % len(listNew)
    listOld = []
    if oldTar:
        print '  building listOld...',
        listOld = buildTarInfoList(oldTar)
        print '  done (%d files)' % len(listOld)

    listOut = filter(lambda x: filterModified(x, listOld), listNew)
    print '  done (%d files)' % len(listOut)
    print ''

    print '  detecting removed files...',
    listRemoved = filter(lambda x: filterRemoved(x, listNew), listOld)
    for r in listRemoved:
        print >> sys.stderr, ':removed:%4s:%10d:%s' % (r.filetypestr(), r.size(), r.name())

    # Output file/output log
    for o in listOut:
        print >> sys.stderr, ':modified:%4s:%10d:%s' % (o.filetypestr(), o.size(), o.name())
    if outputfile:
        print '  creating output archive %s' % outputfile
        fileName, fileExtension = os.path.splitext(outputfile)
        fileExtension = re.sub("[\\.]", '', fileExtension)           # remove the '.'
        outputType = 'w' if 'tar' in fileExtension else ('w:' + fileExtension)
        outTar = tarfile.open(outputfile, outputType)
        for o in listOut:
            print '  adding %s %s%s' % (o.name(), '-> ' if o.issym() else \
                '', o.linkname() if o.issym() else '')
            outTar.addfile(o.tarinfo, o.fileobj)

        outTar.close()

    newTar.close()
    if oldTar:
        oldTar.close()


if __name__ == '__main__':
    main(sys.argv[1:])
