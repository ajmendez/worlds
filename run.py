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
STREAM_PINGPONG = 'pingpong' # interesting...
STREAM_TEXT = 'text'



PARAMS = {
    # travel
    # 'display01_world':{
    #     'display_width':    800,
    #     'display_height':   480,
    #     'width':            200,
    #     'height':           200,
    #     'crop_height':      1080,
    #     'crop_width':       1080,
    #
    #     'num_images':       16,
    #     'ha':               'center',
    #     'va':               'center'
    # },
    
    # pi camera
    'display03_world':{
        'display_width':    1280,
        'display_height':   720,
        'width':            320,
        'height':           320,
        # 'crop_height':      1080,
        # 'crop_width':       1080,
        
        'num_images':       8,
        'ha':               'center',
        'va':               'center',
        'shape':            'square',
        'effects':          [STREAM_PINGPONG, STREAM_TEXT],
        'exclude_index':    [2,3],
    },
    
    'display03_fullscreen':{
        'display_width':    1280,
        'display_height':   720,
        'width':            1280,
        'height':           720,
        # 'crop_height':      1080,
        # 'crop_width':       1080,
        
        'num_images':       8,
        'ha':               'center',
        'va':               'center',
        'shape':            'output',
        'effects':          [STREAM_TEXT],
        'exclude_index':    [],
    },
    
    
    'display03_youtube':{
        'display_width':    1280,
        'display_height':   720,
        'width':            640,
        'height':           360,
        # 'crop_height':      1080,
        # 'crop_width':       1080,
        
        'num_images':       4,
        'ha':               'center',
        'va':               'center',
        'shape':            'output',
        'effects':          [STREAM_TEXT],
        'exclude_index':    [1],
    },
    
    
    
    # TV
    # 'display05_world':{
    #     'display_width':    1920,
    #     'display_height':   1080,
    #     'width':            240, # 8
    #     'height':           240,
    #     'crop_height':      1080,
    #     'crop_width':       1080,
    #
    #     'num_images':       32,
    #     'shape':            'square',
    #     'ha':               'center',
    #     'va':               'center',
    # },
    # 'display05_travel':{
    #     'display_width':    1920,
    #     'display_height':   1080,
    #     #'height':           360,
    #     #'width':            640, # 3
    #     #'num_images':       9,
    #     'height':           270,
    #     'width':            480, # 4
    #     'num_images':       16,
    #
    #     'crop_height':      1080,
    #     'crop_width':       1920,
    #
    #
    #     'ha':               'center',
    #     'va':               'center',
    # },
    
}

DEFAULT_DEVICE = 'display01'
MODE='world'

DEFAULT_DEVICE = 'display05'
MODE='world'

DEFAULT_DEVICE = 'display05'
MODE='travel'


DEFAULT_DEVICE = 'display03'
MODE='fullscreen'


DEFAULT_DEVICE = 'display03'
MODE='youtube'





class Config(object):
    '''Configuration for the video processing'''
    def __init__(self, device_id=DEFAULT_DEVICE, dt=NOW, mode=MODE):
        self.dt = dt
        self.device_id = device_id
        self.mode = mode
        self.debug = False
        # self.display_width,self.display_height = DISPLAY_PARAMS[device_id]
        
        self.tag = '{device_id}_{mode}'.format(**locals())
        for k,v in PARAMS[self.tag].items():
            setattr(self, k, v)
        
        self.border_color = 'LightSteelBlue'
        
        self.in_pattern = '/Volumes/photo/_worlds/{mode}/*'.format(**locals())
        self.crop_pattern = '_{mode}_{dt:%Y-%m-%d}_{{i:02d}}.mkv'.format(**locals())
        self.final_pattern = '{device_id}_{mode}_{dt:%Y-%m-%d}.mkv'.format(**locals())
        
        # self.in_pattern = '/Volumes/photo/_worlds/{mode}/*.gif'.format(**locals())
        
    def get_raw(self):
        '''Gets the raw filenames for the windows'''
        filenames = glob(self.in_pattern)
        assert len(filenames) > 0, IOError('No input images cound')
        if len(filenames) <= self.num_images:
            return filenames
            
        np.random.seed(self.dt.toordinal())
        raw = np.random.choice(filenames, self.num_images, replace=False)
        return raw
    
    def get_metadata(self, filenames):
        with exiftool.ExifTool() as et:
            print(filenames)
            metadata = et.get_metadata_batch(filenames)
        
        for meta in metadata:
            # 'File:FileModifyDate': '2019:01:12 15:07:34-08:00',
            # replace fixes %z 
            meta['dt'] = datetime.strptime(meta['File:FileModifyDate'].replace(':',''), 
                                            '%Y%m%d %H%M%S%z')
            
            meta['title'] = meta['dt'].strftime('%B %Y')
            
            if self.shape == 'square':
                meta['w'] = meta['h'] = meta['QuickTime:ImageHeight']
                meta['x'] = int( (meta['QuickTime:ImageWidth'] - meta['QuickTime:ImageHeight'])/2.0 )
                meta['y'] = 0
            # elif self.shape == 'output':
            #     pass
            else:
                meta['x'] = 0
                meta['y'] = 0
                meta['w'] = meta['QuickTime:ImageWidth']
                meta['h'] = meta['QuickTime:ImageHeight']
        return metadata



class Renderer(object):
    def __init__(self, config):
        self.config = config
        self.nx = int(config.display_width / config.width)
        self.ny = int(config.display_height / config.height)
        self.xy = product(range(self.nx), range(self.ny))
        self.ji = product(range(self.ny), range(self.nx))
        
        self.ox = int( (config.display_width  - self.nx*config.width)/2 )
        self.oy = int( (config.display_height - self.ny*config.height)/2 )
        self.resolution='{config.display_width}x{config.display_height}'.format(**locals())
        self.panel_resolution = '{config.width}x{config.height}'.format(**locals())
    
    def write(self, output_filename, stream, **kwargs):
        params = dict(
            # movflags='+faststart',
            tune='film',
            # crf=17, 
            # preset='slow',
            # format='h264',
            pix_fmt='yuv420p'
        )
        params.update(kwargs)
        
        stream = stream.output(output_filename, **params)
        stream = stream.overwrite_output()
        if config.debug:
            pprint(ffmpeg.get_args(stream))
        stream = stream.run()
        print(stream)

    
    def pingpong(self, video, meta, frac_offset=0):
        start = 0
        end = int(meta['QuickTime:TrackDuration']*meta['QuickTime:VideoFrameRate'])
        mid = int( (end-start)*frac_offset )
        v = video.filter_multi_output('split', 3)
        parts = [
            v[0].trim(start_frame=mid, end_frame=end),
            v[1].filter('reverse')
        ]
        if start != mid:
            parts.append(v[2].trim(start_frame=start, end_frame=mid))
        
        return ffmpeg.concat(*parts).filter('loop')
    
    def title(self, video, name, meta):
        return (video
        
        # .drawtext(name,
        #           x='(w-text_w-5)',
        #           y='(h-text_h-5)',
        #           escape_text=False,
        #
        #           alpha=0.9, fontcolor='white',
        #           fontsize=12,
        #           # box=2, boxcolor='black',
        #           borderw=2, bordercolor='LightSteelBlue@0.5', )
        
        .drawtext(meta['title'], 
                  x='(w-text_w)',
                  y='0',
                  # escape_text=False,
                  
                  alpha=0.8, fontcolor='black', 
                  fontsize=12,
                  # box=2, boxcolor='black',
                  borderw=1, bordercolor='LightSteelBlue@0.7', )
        )
    
    
    def mosaic(self, metadata):
        
        config = self.config
        num_videos = len(metadata)
        stream = None
        max_duration = max([meta['QuickTime:Duration'] for meta in metadata])
        print(max_duration)
        # max_duration=20
        
        for index,((j,i), meta) in enumerate(zip(self.ji, metadata)):
            
            if index in config.exclude_index:
                continue
            
            x = self.ox + (i*config.width) % config.display_width
            y = self.oy + (j*config.height) % config.display_height
            name = 'video_{index}_{i}_{j} '.format(**locals())
            
            pprint(meta)
            
            # -fflags +genpts -stream_loop -1
            video = (
                ffmpeg
                .input(meta['SourceFile'], stream_loop=-1, t=max_duration)
                .filter('crop', meta['w'],meta['h'],meta['x'],meta['y'])
                .filter('scale', self.panel_resolution) 
                .filter('fade', t='in', start_time=0, duration=5)
                .filter('fade', t='out', start_time=max_duration-5, duration=5)
                )
            
            if STREAM_PINGPONG in config.effects:
                video = self.pingpong(video, meta, index/num_videos)
            elif STREAM_TEXT in config.effects:
                video = self.title(video, name, meta)
            video = (video
                      .setpts('PTS-STARTPTS')
                      .drawbox(x=0, y=0, 
                               width=config.width, 
                               height=config.height, 
                               color=config.border_color, thickness=1)
                      )
            if stream is None:
                stream = (video
                          # Align first video with all of the others
                          .filter('pad', x=x,y=y,
                                   height=config.display_height, 
                                   width=config.display_width) )
            else:
                stream = ffmpeg.overlay(stream, video, x=x, y=y)
        
        # stream = stream.filter('loop', 2)
        output_filename = self.config.final_pattern.format(**locals())
        self.write(output_filename, stream)
        
        return output_filename
    
    def concatenate(self, metadata):
        config = self.config
        
        videos = []
        for index, meta in enumerate(metadata):
            # print(index,j,i,meta['title'])
            video = (
                ffmpeg
                .input(meta['SourceFile'])
                # .filter('crop', meta['w'],meta['h'],meta['x'],meta['y'])
                .filter('scale', self.resolution, force_original_aspect_ratio='decrease') 
                .filter('pad', 
                        x=0, #x='((out_w - in_w)/2)', 
                        y='((out_h - in_h)/2)',
                        w=self.config.display_width, h=self.config.display_height)
                .filter('fps', fps=12)
                )
        
            if STREAM_PINGPONG in config.effects:
                video = self.pingpong(video, meta, index/num_videos)
            elif STREAM_TEXT in config.effects:
                video = self.title(video, 'test', meta)
            videos.append(video)
            # break
        output = (
            ffmpeg
            .concat(*videos)
            
             )
        
        output_filename = self.config.final_pattern.format(**locals())
        self.write(output_filename, output)
        return output_filename
            

        
import time
import exiftool
from pprint import pprint

def world(config=None):
    '''Wall of World Videos
    '''
    st = time.time()
    
    raw = config.get_raw()
    metadata = config.get_metadata(raw)
    
    
    renderer = Renderer(config) 
    # 
    if config.mode == 'fullscreen':
        final = renderer.concatenate(metadata)
    else:
        final = renderer.mosaic(metadata)
    
    
    pprint(metadata)
    print(final)
    delta = time.time() - st
    print('Delta: {m:0.0}:{s:0}'.format(m=delta/60.0, s=delta%60))
    # crops = renderer.crop(raw, metadata)
    # final = renderer.world(crops, metadata)
    
    
    # for filename in raw:
        # probe = ffmpeg.probe(filename)
        # video_stream = next((stream for stream in probe['streams']
        #                     if stream['codec_type'] == 'video'), None)
        # print(video_stream)
    


if __name__ == '__main__':
    config = Config()
    world(config)