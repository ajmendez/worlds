#!/usr/bin/env python

import sys
import time
import subprocess
# from time import sleep

def main(filenames):
    try:
        while True:
            global playProcess
            x = 1
            print "LOOPING {x}".format(**locals())
            for filename in filenames:
                print(filename)
                time.sleep(.5)
                command = ['/usr/bin/omxplayer', 
                            # '-v'
                                '--hw',
                                '--loop',
                                '--display=5',
                                '--no-osd',
                                filename
                            ]
                p=subprocess.Popen(command, #shell=True, 
                                                stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE, 
                                                close_fds=True
                                                )
                time.sleep(1)
                # p.stdin.write('q')
                
                prog = ' '.join(command)
                (out,err) = p.communicate()
                out = out[:500]
                if p.returncode == 0:
                        print ("command '%s' succeeded, returned:\n%s" \
                               % (prog, str(out)))
                else:
                    print ("command '%s' failed, exit-code=%d error = %s" \
                           % (prog, p.returncode, str(err)))
                return
                
                
                
                # p.stdin.write('q')
                # (out,err) = p.communicate()
                #
                #     if p.returncode == 0:
                #         print ("command '%s %s' succeeded, returned: %s" \
                #                % (prog, param, str(out)))
                #     elif p.returncode <= 125:
                #         print ("command '%s %s' failed, exit-code=%d error = %s" \
                #                % (prog, param, p.returncode, str(err)))
                #     elif p.returncode == 127:
                #         print ("program '%s' not found: %s" % (prog, str(err)))
                #     else:
                #         # Things get hairy and unportable - different shells return
                #         # different values for coredumps, signals, etc.
                #         sys.exit("'%s' likely crashed, shell retruned code %d" % (cmd,e.returncode))
                
            x += 1
    except IOError as e:
        print(vars(p))
        # p.close()
        raise
    except KeyboardInterrupt:
        print('Bye')


if __name__ == '__main__':
    filenames = sys.argv[1:]
    assert len(filenames) > 0, "Pass in filenames"
    main(filenames)