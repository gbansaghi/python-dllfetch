#!/usr/bin/env python3

import argparse
import os
import re
import shlex
import shutil
import subprocess
import time

DLL_REGEX = re.compile("DLL Name:\s*(\S+)")

def checkFile(filename):
    print("checking dependencies for {}".format(filename))

    command = "objdump -p {}".format(filename)
    result = subprocess.check_output(shlex.split(command)).decode()

    hitnames = set()
    for line in result.splitlines():
        match = DLL_REGEX.search(line)
        if match:
            hitname = match.group(1)
            hitnames.add(hitname)

    return hitnames

class Dependecy():
    _filename = ""
    _filepath = ""
    _checked  = False
    _searched = False
    _found    = False

    def __init__(self, filename):
        self._filename = filename.lower()
        self._regex = re.compile(re.escape(self._filename), re.IGNORECASE)

    def __eq__(self, other):
        return self._filename == other.filename

    def __hash__(self):
        return hash(self._filename)

    @property
    def checked(self):
        return self._checked

    @property
    def found(self):
        return self._found

    @property
    def filename(self):
        return self._filename

    @property
    def filepath(self):
        return self._filepath

    def find(self, dirs):
        if self._searched:
            return
        self._searched = True

        hits = {}
        for directory in dirs:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    if self._regex.fullmatch(filename):
                        # Filenames are unique, directories are not
                        # (e.g. a.dll and A.DLL in the same directory)
                        hits[filename] = dirpath
        if len(hits.items()) == 0:
            print("-", self._filename, "missing")
            self._found = False
            self._checked = True
        elif len(hits.items()) == 1:
            filename, dirpath = list(hits.items())[0]
            self._filepath = os.path.join(dirpath, filename)
            self._found = True
        else:
            print("\n"+self._filename, "found in multiple directories")
            print("please choose one:")
            choices = list(hits.items())
            for filename, dirpath in choices:
                print(" [{}] {}".format(choices.index((filename, dirpath)),
                                        os.path.join(dirpath, filename)))
            while True:
                answer = input('> ')
                idx = -1
                try:
                    idx = int(answer)
                except:
                    pass
                if idx < len(hits):
                    break
                else:
                    print("invalid answer")
            filename, dirpath = list(hits.items())[idx]
            self._filepath = os.path.join(dirpath, filename)
            self._found = True

    def check(self):
        if self._checked:
            return []
        if not self._searched:
            return []
        if not self._found:
            return []
        self._checked = True

        return checkFile(self._filepath)

class DependecyChecker():
    _filename = ""
    _dirs = []
    _deps = set()

    def __init__(self, filename, dirs):
        self._filename = filename
        if dirs:
            self._dirs = dirs
        else:
            self._dirs = ['/']

    def run(self):
        hitnames = checkFile(self._filename)
        for filename in hitnames:
            self.addDependency(filename)

        while len(self.notChecked) > 0:
            for dep in self.notChecked:
                dep.find(self._dirs)
                hitnames = dep.check()
                for filename in hitnames:
                    self.addDependency(filename)

        return self.foundPaths, self.notFoundNames

    def addDependency(self, filename):
        self._deps.add(Dependecy(filename))

    @property
    def checked(self):
        return [i for i in self._deps if i.checked == True]

    @property
    def notChecked(self):
        return [i for i in self._deps if i.checked == False]

    @property
    def found(self):
        return [i for i in self._deps if i.found == True]

    @property
    def notFound(self):
        return [i for i in self._deps if i.found == False]

    @property
    def foundPaths(self):
        return [i.filepath for i in self.found]

    @property
    def notFoundNames(self):
        return [i.filename for i in self.notFound]

def main():
    parser = argparse.ArgumentParser(description='check DLL dependencies')
    parser.add_argument('FILE', help='check the dependencies of this file')
    parser.add_argument('-d', '--dir', nargs='*',
                        help='check for dependencies in these directories')
    parser.add_argument('-t', '--target-dir',
                        help='copy dependencies into this directory')

    args = parser.parse_args()

    checker = DependecyChecker(args.FILE, args.dir)
    found, notfound = checker.run()

    print("\n*** Found dependencies: ***")
    found.sort()
    for filepath in found:
        print('+', filepath)

    print("\n*** Missing dependencies: ***")
    found.sort()
    for filename in notfound:
        print('-', filename)

    if not args.target_dir:
        return

    print('\nCopying files to', args.target_dir)
    for source_path in found:
        source_dir, source_name = os.path.split(source_path)
        print('>', source_name)
        shutil.copy(source_path, args.target_dir)

    print('\nDone!')
if __name__ == '__main__':
    main()
