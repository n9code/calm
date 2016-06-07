import sys
import nose

sys.argv = sys.argv + [
    '-s',
    '-v',
    '--with-coverage',
    '--cover-package=calm',
    '--cover-erase',
]

nose.main()
