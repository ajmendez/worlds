#!/usr/bin/env python


import os

import subprocess
from glob import glob
from datetime import datetime
from itertools import product

import numpy as np
import ffmpeg




_ = datetime.now()
NOW = datetime(_.year, _.month, _.day)

DISPLAY_PARAMS = {
    'display01':(800, 480)
}
PARAMS = {
    'display01_world':{
        'width':        200,
        'height':       200,
        'crop_height':  1080,
        'crop_width':   1080,
        
        'num_images':   16,
        'ha':           'center',
        'va':           'center'
        
    }
    
}



class Config(object):
    '''Configuration for the video processing'''
    def __init__(self, device_id='display01', dt=NOW, mode='world'):
        self.dt = dt
        self.device_id='display01'
        self.display_width,self.display_height = DISPLAY_PARAMS[device_id]
        
        self.tag = '{device_id}_{mode}'.format(**locals())
        for k,v in PARAMS[self.tag].items():
            setattr(self, k, v)
        
        
        self.in_pattern = '/Volumes/photo/_worlds/*.MP4'
        self.crop_pattern = '_crop_{dt:%Y-%m-%d}_{{i:02d}}.mkv'.format(**locals())
        self.final_pattern = 'world_{dt:%Y-%m-%d}.mkv'.format(**locals())
    
    def get_raw(self):
        '''Gets the raw filenames for the windows'''
        filenames = glob(self.in_pattern)
        np.random.seed(self.dt.toordinal())
        raw = np.random.choice(filenames, self.num_images)
        return raw




class Renderer(object):
    def __init__(self, config):
        self.config = config
    
    def _run(self, cmd):
        try:
            if isinstance(cmd, (list, tuple)):
                _cmd = cmd
            else:
                _cmd = cmd.split()
            print(_cmd)
            print(subprocess.check_output(_cmd))
        except KeyboardInterrupt:
            print('bye')
    
    def crop(self, videos):
        '''Crop videos so that they are square'''
        def _ffmpeg_crop(config, filename, i):
            w = config.crop_width
            h = config.crop_height
            x = int( (1920-w)/2.0 )
            y = int( (1080-h)/2.0 )
            output_filename = config.crop_pattern.format(**locals())
            
            cmd = 'ffmpeg -y -i {filename} -filter:v crop={w}:{h}:{x}:{y} {output_filename}'.format(**locals())
            
            if not os.path.exists(output_filename):
                self._run(cmd)
            return output_filename
        
        crops = [_ffmpeg_crop(self.config, filename, i)
                 for i, filename in enumerate(videos)]
        return crops
    
    
    def world(self, videos):
        '''Grid of videos'''
        
        # def _filter_complex(config, filenames):
        #     nx = int(config.display_width / config.width)
        #     ny = int(config.display_height / config.height)
        #     xy = product(range(nx), range(ny))
        #
        #     ox = int( (config.display_width - nx*config.width)/2 )
        #     oy = int( (config.display_height - ny*config.height)/2 )
        #
        #     resolution='{config.display_width}x{config.display_height}'.format(**locals())
        #     panel_resolution = '{config.width}x{config.height}'.format(**locals())
        #
        #     start_template = '[{index}:v] setpts=PTS-STARTPTS, scale={panel_resolution} [{name}];'
        #     combine_template = '[{prev_name}][{name}] overlay=shortest=1:x={x}:y={y} [{next_name}];'
        #
        #     prev_name = 'base'
        #     filter_complex = '''nullsrc=size=640x480 [{prev_name}];'''.format(**locals())
        #     second_complex = ''
        #     for index,((i,j),filename) in enumerate(zip(xy, videos)):
        #         x = ox + (i*config.width) % config.display_width
        #         y = oy + (j*config.height) % config.display_height
        #
        #         name = 'video_{i}_{j}'.format(**locals())
        #         next_name = 'tmp_{index}'.format(**locals())
        #         filter_complex += start_template.format(**locals())
        #         second_complex += combine_template.format(**locals())
        #         prev_name = next_name
        #
        #     return filter_complex + second_complex
        
        # inputs = ' '.join(['-i {filename}\n'.format(**locals())
        #                     for filename in videos])
        # filter_complex = _filter_complex(self.config, videos)
        
        # output_filename = self.config.final_pattern.format(**locals())
        # output_values = '-c:v libx264 {output_filename}'.format(**locals())
        
        # cmd = '''ffmpeg -y {inputs} -filter_complex {filter_complex} {output_values}'''.format(**locals())
        
        
        
        
        config = self.config
        nx = int(config.display_width / config.width)
        ny = int(config.display_height / config.height)
        xy = product(range(nx), range(ny))
        
        ox = int( (config.display_width - nx*config.width)/2 )
        oy = int( (config.display_height - ny*config.height)/2 )
        resolution='{config.display_width}x{config.display_height}'.format(**locals())
        panel_resolution = '{config.width}x{config.height}'.format(**locals())
        
        
        #https://github.com/kkroening/ffmpeg-python/issues/121
        
        
        # stream = ffmpeg.input(videos[0])
        # stream = (ffmpeg
        #           .drawbox(50, 50, 120, 120, color='red', thickness=5)
        #           .filter('nullsrc', size=resolution) )
        # stream = ffmpeg.FilterNode()
        # stream = (ffmpeg
        #          .input('pipe:')
        #          .filter(None, 'nullsrc', size=resolution))
        
        
        stream = None
        for index,((i,j),filename) in enumerate(zip(xy, videos)):
            if index > 2:
                break
                
            x = ox + (i*config.width) % config.display_width
            y = oy + (j*config.height) % config.display_height
            name = 'video_{i}_{j}'.format(**locals())
            
            video = (ffmpeg.input(filename)
                      .setpts('PTS-STARTPTS')
                      .filter('scale', panel_resolution)
                      # .drawtext(text=name, x=x, y=y, )
                      .drawbox(x=x, y=y, width=config.width, height=config.height, color='red')
                      )
            if stream is None:
                stream = (video
                          # .filter('offset', )
                          .filter('pad', x=x,y=y,
                                   height=config.display_height, 
                                   width=config.display_width) )
            else:
                stream = ffmpeg.overlay(stream, video, x=x, y=y, shortest=1)
        
        output_filename = self.config.final_pattern.format(**locals())
        stream = stream.output(output_filename)
        #, format='h264'
        stream = stream.overwrite_output()
        stream = stream.run()
        return output_filename
        
        
       #  https://github.com/varenc/homebrew-ffmpeg
       # brew tap varenc/ffmpeg
       # brew install varenc/ffmpeg/ffmpeg
       # brew options varenc/ffmpeg/ffmpeg
       
        #https://trac.ffmpeg.org/wiki/Create%20a%20mosaic%20out%20of%20several%20input%20videos
        #https://www.raspberrypi.org/documentation/raspbian/applications/omxplayer.md
        #https://github.com/kkroening/ffmpeg-python/blob/master/ffmpeg/_filters.py#L28
                #
        #
        # cmd = ['ffmpeg', '-y']
        # for filename in videos:
        #     cmd += ['-i', filename]
        #
        # filter_complex = _filter_complex(self.config, videos)
        # cmd += ['-filter_complex', filter_complex ]
        #
        # output_filename = self.config.final_pattern.format(**locals())
        # cmd += ['-c:v', 'libx264', output_filename]
        #
        # # print('\n'.join(cmd))
        # self._run(cmd)
        # return output_filename
        #
       #
#
            # ffmpeg -i input.mp4 \
            # -vf crop=1424:720:0:40,scale=1280:720,setsar=1 -c:a copy output.mp4
            
#
# single:
#     ffmpeg \
#         -i /Volumes/photo/_worlds/DJI_0586.MP4 \
#         -i /Volumes/photo/_worlds/DJI_0572.MP4 \
#         -i /Volumes/photo/_worlds/DJI_0566.MP4 \
#         -i /Volumes/photo/_worlds/DJI_0573.MP4 \
#         -filter_complex " \
#             nullsrc=size=$(RES) [base]; \
#             [0:v] setpts=PTS-STARTPTS, scale=$(RES_HALF) [upperleft]; \
#             [1:v] setpts=PTS-STARTPTS, scale=$(RES_HALF) [upperright]; \
#             [2:v] setpts=PTS-STARTPTS, scale=$(RES_HALF) [lowerleft]; \
#             [3:v] setpts=PTS-STARTPTS, scale=$(RES_HALF) [lowerright]; \
#             [base][upperleft] overlay=shortest=1 [tmp1]; \
#             [tmp1][upperright] overlay=shortest=1:x=$(X_HALF) [tmp2]; \
#             [tmp2][lowerleft] overlay=shortest=1:y=$(Y_HALF) [tmp3]; \
#             [tmp3][lowerright] overlay=shortest=1:x=$(X_HALF):y=$(Y_HALF) " \
#         -c:v libx264 output.mkv


def world(config=None):
    '''Wall of World Videos
    '''
    raw = config.get_raw()
    
    renderer = Renderer(config)
    crops = renderer.crop(raw)
    final = renderer.world(crops)
    print(final)
    # crops = get_crops(config, raw)
    # final = get_final(config, crops)
    
    
    
    
    


if __name__ == '__main__':
    config = Config()
    world(config)