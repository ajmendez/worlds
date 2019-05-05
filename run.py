#!/usr/bin/env python


import os

import subprocess
from glob import glob
from datetime import datetime
from itertools import product

import numpy as np
import ffmpeg

        
       #  https://github.com/varenc/homebrew-ffmpeg
       # brew tap varenc/ffmpeg
       # brew install varenc/ffmpeg/ffmpeg
       # brew options varenc/ffmpeg/ffmpeg
       
        #https://trac.ffmpeg.org/wiki/Create%20a%20mosaic%20out%20of%20several%20input%20videos
        #https://www.raspberrypi.org/documentation/raspbian/applications/omxplayer.md
        #https://github.com/kkroening/ffmpeg-python/blob/master/ffmpeg/_filters.py#L28



_ = datetime.now()
NOW = datetime(_.year, _.month, _.day)

PARAMS = {
    'display01_world':{
        'display_width':    800,
        'display_height':   480,
        'width':            200,
        'height':           200,
        'crop_height':      1080,
        'crop_width':       1080,
                            
        'num_images':       16,
        'ha':               'center',
        'va':               'center'
    },
    'display05_world':{
        'display_width':    1920,
        'display_height':   1080,
        'width':            240, # 8
        'height':           240,
        'crop_height':      1080,
        'crop_width':       1080,
                            
        'num_images':       32,
        'ha':               'center',
        'va':               'center'
    },
    'display05_travel':{
        'display_width':    1920,
        'display_height':   1080,
        'height':           360,
        'width':            640, # 3
        'crop_height':      1080,
        'crop_width':       1920,
                            
        'num_images':       9,
        'ha':               'center',
        'va':               'center'
    },
    
}

DEFAULT_DEVICE = 'display01'
MODE='world'

DEFAULT_DEVICE = 'display05'
MODE='world'

DEFAULT_DEVICE = 'display05'
MODE='travel'


class Config(object):
    '''Configuration for the video processing'''
    def __init__(self, device_id=DEFAULT_DEVICE, dt=NOW, mode=MODE):
        self.dt = dt
        self.device_id = device_id
        self.mode = mode
        # self.display_width,self.display_height = DISPLAY_PARAMS[device_id]
        
        self.tag = '{device_id}_{mode}'.format(**locals())
        for k,v in PARAMS[self.tag].items():
            setattr(self, k, v)
        
        self.border_color = 'LightSteelBlue'
        
        self.in_pattern = '/Volumes/photo/_worlds/{mode}/*.MP4'.format(**locals())
        self.crop_pattern = '_{mode}_{dt:%Y-%m-%d}_{{i:02d}}.mkv'.format(**locals())
        self.final_pattern = '{device_id}_{mode}_{dt:%Y-%m-%d}.mkv'.format(**locals())
    
    def get_raw(self):
        '''Gets the raw filenames for the windows'''
        filenames = glob(self.in_pattern)
        if len(filenames) < self.num_images:
            return filenames
            
        np.random.seed(self.dt.toordinal())
        raw = np.random.choice(filenames, self.num_images, replace=False)
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
        config = self.config
        w = config.crop_width
        h = config.crop_height
        x = int( (1920-w)/2.0 )
        y = int( (1080-h)/2.0 )
        panel_resolution = '{config.width}x{config.height}'.format(**locals())
        
        outputs = []
        for i, filename in enumerate(videos):
            output_filename = config.crop_pattern.format(**locals())
            outputs.append(output_filename)
            
            if os.path.exists(output_filename):
                continue
            (ffmpeg
                .input(filename)
                .filter('crop', w,h,x,y)
                .filter('scale', panel_resolution)
                .output(output_filename, pix_fmt='yuv420p')
                .run()
                )
            print(output_filename)
        return outputs
    
    
    def world(self, videos, metadata):
        '''Grid of videos'''
        
        config = self.config
        nx = int(config.display_width / config.width)
        ny = int(config.display_height / config.height)
        xy = product(range(nx), range(ny))
        ji = product(range(ny), range(nx))
        
        ox = int( (config.display_width - nx*config.width)/2 )
        oy = int( (config.display_height - ny*config.height)/2 )
        resolution='{config.display_width}x{config.display_height}'.format(**locals())
        panel_resolution = '{config.width}x{config.height}'.format(**locals())
        
        stream = None
        for index,((j,i),filename, meta) in enumerate(zip(ji, videos, metadata)):
            # if index > 2:
            #     break
                
            x = ox + (i*config.width) % config.display_width
            y = oy + (j*config.height) % config.display_height
            name = 'video_{i}_{j} '.format(**locals())
            name = '{meta[File:FileInodeChangeDate]}'.format(**locals())
            offset = index*60*10
            
            in_file = ffmpeg.input(filename)
            
            if config.mode == 'world':
                start = 0
                end = int(meta['QuickTime:TrackDuration']*meta['QuickTime:VideoFrameRate'])
                mid = int( (end-start)*index/len(videos) )
                unit = (
                    ffmpeg
                    .concat(in_file.trim(start_frame=mid, end_frame=end),
                            in_file.filter('reverse'),
                            in_file.trim(start_frame=start, end_frame=mid))
                )
            else:
                unit = in_file
                
            
            video = (unit
                      .setpts('PTS-STARTPTS')
                      .filter('scale', panel_resolution)
                      .drawtext(name, 
                                x='(w-text_w-5)',
                                y='(h-text_h-5)',
                                alpha=0.9, fontcolor='white', 
                                fontsize=12,
                                # box=2, boxcolor='black',
                                borderw=2, bordercolor='LightSteelBlue@0.5', )
                      .drawbox(x=0, y=0, 
                               width=config.width, 
                               height=config.height, 
                               color=config.border_color, thickness=1)
                      )
            if stream is None:
                stream = (video
                          # .filter('offset', )
                          .filter('pad', x=x,y=y,
                                   height=config.display_height, 
                                   width=config.display_width) )
            else:
                #, shortest=1
                stream = ffmpeg.overlay(stream, video, x=x, y=y)
        
        # stream = stream.filter('loop', 2)
        output_filename = self.config.final_pattern.format(**locals())
        stream = stream.output(output_filename, 
                                movflags='+faststart', 
                                tune='film', 
                                crf=17, 
                                preset='slow', 
                                pix_fmt='yuv420p')
        #, format='h264'
        
        stream = stream.overwrite_output()
        stream = stream.run()
        return output_filename
        
        

import exiftool
from pprint import pprint

def world(config=None):
    '''Wall of World Videos
    '''
    raw = config.get_raw()
    with exiftool.ExifTool() as et:
        metadata = et.get_metadata_batch(raw)
    # pprint(metadata)
    # return
    
    renderer = Renderer(config)
    crops = renderer.crop(raw)
    final = renderer.world(crops, metadata)
    
    
    pprint(metadata[0])
    
    print(final)
    
    # for filename in raw:
        # probe = ffmpeg.probe(filename)
        # video_stream = next((stream for stream in probe['streams']
        #                     if stream['codec_type'] == 'video'), None)
        # print(video_stream)
    


if __name__ == '__main__':
    config = Config()
    world(config)