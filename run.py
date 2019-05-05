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
PINGPONG = 'pingpong' # interesting...



PARAMS = {
    # travel
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
        'effects':          [PINGPONG],
        'exclude_index':    [2,3],
        
    },
    
    # TV
    'display05_world':{
        'display_width':    1920,
        'display_height':   1080,
        'width':            240, # 8
        'height':           240,
        'crop_height':      1080,
        'crop_width':       1080,
                            
        'num_images':       32,
        'shape':            'square',
        'ha':               'center',
        'va':               'center',
    },
    'display05_travel':{
        'display_width':    1920,
        'display_height':   1080,
        #'height':           360,
        #'width':            640, # 3
        #'num_images':       9,
        'height':           270,
        'width':            480, # 4
        'num_images':       16,
        
        'crop_height':      1080,
        'crop_width':       1920,
                            
        
        'ha':               'center',
        'va':               'center',
    },
    
}

DEFAULT_DEVICE = 'display01'
MODE='world'

DEFAULT_DEVICE = 'display05'
MODE='world'

DEFAULT_DEVICE = 'display05'
MODE='travel'


DEFAULT_DEVICE = 'display03'
MODE='world'







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
    
    def get_metadata(self, filenames):
        with exiftool.ExifTool() as et:
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
        
        return ffmpeg.concat(*parts)
    
    def title(self, video, name, meta):
        return (video
        
        .drawtext(name, 
                  x='(w-text_w-5)',
                  y='(h-text_h-5)',
                  escape_text=False,
                  
                  alpha=0.9, fontcolor='white', 
                  fontsize=12,
                  # box=2, boxcolor='black',
                  borderw=2, bordercolor='LightSteelBlue@0.5', )
        
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
        for index,((j,i), meta) in enumerate(zip(self.ji, metadata)):
            
            if index in config.exclude_index:
                continue
            
            x = self.ox + (i*config.width) % config.display_width
            y = self.oy + (j*config.height) % config.display_height
            name = 'video_{index}_{i}_{j} '.format(**locals())
            
            
            video = (
                ffmpeg
                .input(meta['SourceFile'])
                .filter('crop', meta['w'],meta['h'],meta['x'],meta['y'])
                .filter('scale', self.panel_resolution) )
            
            if PINGPONG in config.effects:
                video = self.pingpong(video, meta, index/num_videos)
            elif TEXT in config.effects:
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
        stream = stream.output(output_filename, 
                                movflags='+faststart', 
                                tune='film', 
                                crf=17, 
                                preset='slow', 
                                format='h264',
                                pix_fmt='yuv420p')
        #, format='h264'
        
        stream = stream.overwrite_output()
        
        pprint(ffmpeg.get_args(stream))
        stream = stream.run()
        return output_filename
    
    
    # def _run(self, cmd):
    #     try:
    #         if isinstance(cmd, (list, tuple)):
    #             _cmd = cmd
    #         else:
    #             _cmd = cmd.split()
    #         print(_cmd)
    #         print(subprocess.check_output(_cmd))
    #     except KeyboardInterrupt:
    #         print('bye')
    
    
    
    
    # def crop(self, videos, metadata):
    #     '''Crop videos so that they are square'''
    #     config = self.config
    #     w = config.crop_width
    #     h = config.crop_height
    #     x = int( (1920-w)/2.0 )
    #     y = int( (1080-h)/2.0 )
    #     panel_resolution = '{config.width}x{config.height}'.format(**locals())
    #
    #     outputs = []
    #     for i, (filename, meta) in enumerate(zip(videos,metadata)):
    #         output_filename = config.crop_pattern.format(**locals())
    #         outputs.append(output_filename)
    #
    #         if os.path.exists(output_filename):
    #             continue
    #         (ffmpeg
    #             .input(filename)
    #             .filter('crop', w,h,x,y)
    #             .filter('scale', panel_resolution)
    #             .output(output_filename, pix_fmt='yuv420p')
    #             .run()
    #             )
    #         print(output_filename)
    #     return outputs
    
    
    
    
    # def world(self, videos, metadata):
    #     '''Grid of videos'''
    #
    #     config = self.config
    #     nx = int(config.display_width / config.width)
    #     ny = int(config.display_height / config.height)
    #     xy = product(range(nx), range(ny))
    #     ji = product(range(ny), range(nx))
    #
    #     ox = int( (config.display_width - nx*config.width)/2 )
    #     oy = int( (config.display_height - ny*config.height)/2 )
    #     resolution='{config.display_width}x{config.display_height}'.format(**locals())
    #     panel_resolution = '{config.width}x{config.height}'.format(**locals())
    #
    #     stream = None
    #     for index,((j,i),filename, meta) in enumerate(zip(ji, videos, metadata)):
    #         # if index > 2:
    #         #     break
    #
    #         x = ox + (i*config.width) % config.display_width
    #         y = oy + (j*config.height) % config.display_height
    #         name = 'video_{i}_{j} '.format(**locals())
    #
    #         name = '{meta[File:FileInodeChangeDate]}'.format(**locals())
    #         offset = index*60*10
    #
    #         in_file = ffmpeg.input(filename)
    #
    #         if config.mode == 'world':
    #             start = 0
    #             end = int(meta['QuickTime:TrackDuration']*meta['QuickTime:VideoFrameRate'])
    #             mid = int( (end-start)*index/len(videos) )
    #             unit = (
    #                 ffmpeg
    #                 .concat(in_file.trim(start_frame=mid, end_frame=end),
    #                         in_file.filter('reverse'),
    #                         in_file.trim(start_frame=start, end_frame=mid))
    #             )
    #         else:
    #             unit = in_file
    #
    #
    #         video = (unit
    #                   .setpts('PTS-STARTPTS')
    #                   .filter('scale', panel_resolution)
    #                   .drawtext(name,
    #                             x='(w-text_w-5)',
    #                             y='(h-text_h-5)',
    #                             alpha=0.9, fontcolor='white',
    #                             fontsize=12,
    #                             # box=2, boxcolor='black',
    #                             borderw=2, bordercolor='LightSteelBlue@0.5', )
    #                   .drawbox(x=0, y=0,
    #                            width=config.width,
    #                            height=config.height,
    #                            color=config.border_color, thickness=1)
    #                   )
    #         if stream is None:
    #             stream = (video
    #                       # .filter('offset', )
    #                       .filter('pad', x=x,y=y,
    #                                height=config.display_height,
    #                                width=config.display_width) )
    #         else:
    #             #, shortest=1
    #             stream = ffmpeg.overlay(stream, video, x=x, y=y)
    #
    #     # stream = stream.filter('loop', 2)
    #     output_filename = self.config.final_pattern.format(**locals())
    #     stream = stream.output(output_filename,
    #                             movflags='+faststart',
    #                             tune='film',
    #                             crf=17,
    #                             preset='slow',
    #                             pix_fmt='yuv420p')
    #     #, format='h264'
    #
    #     stream = stream.overwrite_output()
    #     stream = stream.run()
    #     return output_filename
        
        

import exiftool
from pprint import pprint

def world(config=None):
    '''Wall of World Videos
    '''
    raw = config.get_raw()
    metadata = config.get_metadata(raw)
    
    
    renderer = Renderer(config) 
    # final = renderer.mosaic(metadata)
    # final = renderer.
    
    
    pprint(metadata[0])
    print(final)
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