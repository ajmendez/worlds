#!/usr/bin/env python


# https://github.com/willprice/python-omxplayer-wrapper
import sys
import time
from omxplayer import OMXPlayer
from omxplayer.player import OMXPlayerDeadError
from dbus.exceptions import DBusException


NUM_LOOPS = 20



def _single(files, args):
    player = OMXPlayer(files[0], args=args)
    # sleep(2)
    while True:
        try:
            for filename in files:
                print(filename)
                player.load(filename)
                for i in range(NUM_LOOPS):
                    print(i)
                    # player.load(filename)
                    player.set_position(0.0)
                    player.play_sync()
        except KeyboardInterrupt:
            player.quit()
            return
        except (DBusException,OMXPlayerDeadError) as e:
            print(e)
            player.quit()
            
            player = OMXPlayer(filename, args=args)



def _perfile(files, args):
    players = []
    for filename in files:
        player = OMXPlayer(filename, args=args, pause=True)
        # player.set_alpha(0)
        player.pause()
        player.hide_video()
        players.append(player)
    time.sleep(2)
    
    while True:
        for player in players:
            # print(player)
            # time.sleep(player.duration()-1)
            try:
                filename = player.get_source()
                duration = player.duration()
                print(filename, duration)
                # player.set_alpha(1.0)
                player.show_video()
                for i in range(2):
                    print(i)
                    player.set_position(0.0)
                    
                    # player.play_sync()
                    player.play()
                    time.sleep(duration-0.1)
                
                
                # while player.is_playing():
                #     time.sleep(0.25)
                #     print(filename)
                #     # print('.')
                #     # print(filename, player.width(), player.height())
                # player.pause()
                player.hide_video()
            except OMXPlayerDeadError as e:
                print(e)
                player.load(filename, pause=True)
            
            except Exception as e:
                print(e)
                raise
                # player.quit()
                
                # RPOEBLM
                # player = OMXPlayer(filename, args=args, pause=True)
                # player.set_alpha(0)
                # player.hide_video()
                
                # player.load(filename, pause=True)
            
            # player.set_alpha(0.0)


def main(files):
    args=['--no-osd', '--hw', '--display=5']
    try:
        _single(files, args)
        
        # _perfile(files, args)
    except KeyboardInterrupt:
        print('Bye')

    print('Quiting')
    

if __name__ == '__main__':
    files = sys.argv[1:]
    main(files)
