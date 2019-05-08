#!/usr/bin/env python


import os

import subprocess
from glob import glob
from datetime import datetime
from itertools import product

import numpy as np
import ffmpeg

        

        
import time
import exiftool
from pprint import pprint



_ = datetime.now()
NOW = datetime(_.year, _.month, _.day)
STREAM_PINGPONG = 'pingpong' # interesting...
STREAM_TEXT = 'text'
STREAM_CIRCLE = 'circle'
STREAM_FADE = 'fade'




# TODO break this up into device stats and other
DEVICES = {
    'display03':{
        'display_width':    1280,
        'display_height':   720,
        'width':            320,
        'height':           320,

    },
    'display01':{
        'display_width':    800,
        'display_height':   480,
        'width':            200,
        'height':           200,
    },
    'display03':{
        'display_width':    1920,
        'display_height':   1080,
        'width':            240, # 8
        'height':           240,
        #     #     #'height':           360,
        #     #     #'width':            640, # 3
        #     #     #'num_images':       9,
    }
}
MODES = {
    'world':{
        'shape':            'square',
        'effects':          [STREAM_PINGPONG, 
                             STREAM_CIRCLE, 
                             STREAM_TEXT],
        'rows':             2,
        'cols':             4,
        'num_images':       8,
        'exclude_index':    [2,3],
    },
    'fullscreen':{
        'shape':            'output',
        'effects':          [STREAM_TEXT],
        'rows':             1,
        'cols':             1,
        'num_images':       32,
        'exclude_index':    [],
    },
    'youtube': {
        'shape':            'output',
        'effects':          [STREAM_TEXT, STREAM_FADE],
        'rows':             1,
        'cols':             2,
        'num_images':       2,
        'exclude_index':    [1],
    },
    'timelapse': {
        'shape':            'output',
        'effects':          [STREAM_FADE],
        'rows':             1,
        'cols':             1,
        'num_images':       None,
        'exclude_index':    [],
    }
}


# DEFAULT_DEVICE = 'display01'
# MODE='world'
#
# DEFAULT_DEVICE = 'display05'
# MODE='world'
#
# DEFAULT_DEVICE = 'display05'
# MODE='travel'
#
#
# DEFAULT_DEVICE = 'display03'
# MODE='fullscreen'
#
#
DEFAULT_DEVICE = 'display03'
# MODE='youtube'
# MODE='world'
MODE='timelapse'


# from ffmpeg._filter import filter_operator, FilterNode
from ffmpeg.nodes import FilterNode, filter_operator


@filter_operator()
def alphamerge(main_parent_node, overlay_parent_node, **kwargs):
    """Add or replace the alpha component of the primary input with the grayscale value of a second input. This is intended for use with alphaextract to allow the transmission or storage of frame sequences that have alpha in a format that doesn’t support an alpha channel.
    For example, to reconstruct full frames from a normal YUV-encoded video and a separate video created with alphaextract, you might use:

        movie=in_alpha.mkv [alpha]; [in][alpha] alphamerge [out]
    
    Since this filter is designed for reconstruction, it operates on frame sequences without considering timestamps, and terminates when either input reaches end of stream. This will cause problems if your encoding pipeline drops frames. If you’re trying to apply an image as an overlay to a video stream, consider the overlay filter instead.
    
    Args:
            
    Official documentation: `overlay <https://ffmpeg.org/ffmpeg-filters.html#alphamerge-1>`__
    """
    return FilterNode([main_parent_node, overlay_parent_node], alphamerge.__name__, 
                      kwargs=kwargs, max_inputs=2).stream()



ffmpeg.alphamerge = alphamerge




class Config(object):
    '''Configuration for the video processing'''
    def __init__(self, device_id=DEFAULT_DEVICE, dt=NOW, mode=MODE):
        self.dt = dt
        self.device_id = device_id
        self.mode = mode
        self.debug = True
        # self.display_width,self.display_height = DISPLAY_PARAMS[device_id]
        
        self.tag = '{device_id}_{mode}'.format(**locals())
        for k,v in MODES[mode].items():
            setattr(self, k, v)
        for k,v in DEVICES[device_id].items():
            setattr(self, k, v)
        # for k,v in PARAMS[self.tag].items():
        #     setattr(self, k, v)
        
        self.border_color = 'LightSteelBlue'
        
        self.in_pattern = '/Volumes/photo/_worlds/{mode}/*'.format(**locals())
        self.crop_pattern = '_{mode}_{dt:%Y-%m-%d}_{{i:02d}}.mkv'.format(**locals())
        self.final_pattern = '{device_id}_{mode}_{dt:%Y-%m-%d}.mkv'.format(**locals())
        
        # self.in_pattern = '/Volumes/photo/_worlds/{mode}/*.gif'.format(**locals())
        
    def get_raw(self):
        '''Gets the raw filenames for the windows'''
        filenames = glob(self.in_pattern)
        assert len(filenames) > 0, IOError('No input images count')
        if (self.num_images is None) or (len(filenames) <= self.num_images):
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
            # tune='film',
            # crf=17, 
            # preset='slow',
            # format='h264',
            pix_fmt='yuv420p'
            # format='qtrle'
        )
        params.update(kwargs)
        
        stream = stream.output(output_filename, **params)
        stream = stream.overwrite_output()
        if config.debug:
            pprint(ffmpeg.get_args(stream))
        stream = stream.run()
        print(stream)

    
    def pingpong(self, video, meta, frac_offset=0):
        print('pingpong')
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
    
    def title(self, video, meta):
        print('title')
        return (video
        .drawtext(meta['title'], 
                  x='(w-text_w)',
                  y='0',
                  alpha=0.8, fontcolor='black', 
                  fontsize=12,
                  borderw=1, bordercolor='LightSteelBlue@0.7', )
        )
    
    def fade(self, video, fade_duration, max_duration):
        print('fade')
        return (video
                .filter('fade', t='in', start_time=0, duration=fade_duration)
                .filter('fade', t='out', start_time=max_duration-fade_duration, 
                        duration=fade_duration) )
    
    def circle(self, video, mask):
        # return video
        # return ffmpeg.overlay(video,mask)
        return (alphamerge(video,mask)
                # .filter('hue', s=0)
                
                )
        # return video.filter('geq', 'lum=255*gauss((X/W-0.5)*3)*gauss((Y/H-0.5)*3)/gauss(0)/gauss(0)')
        # return video.filter('geq', "st(3,pow(X-(W/2),2)+pow(Y-(H/2),2));if(lte(ld(3),200*200),0,255)")
    
    def load_mask(self, name):
        filename = '{name}.png'.format(**locals())
        mask = (
            ffmpeg
            .input(filename, stream_loop=-1, t=self.config.max_duration)
            # .filter('scale', '{}x{}'.format(self.config.height, self.config.height))
            # .filter('pad')
            .filter('alphaextract')
            # .filter('boxblur', 5)
            
            # .filter('scale', '{}x{}'.format(self.config.display_width,
            #                                 self.config.display_height))
            # .filter('setar', 1)
            # .filter('pad', x=0, y=0, h=self.config.display_height,
            #                                 w=self.config.display_width)
            

        )
        return mask
    
    def effects(self, video, config, meta):
        if STREAM_PINGPONG in config.effects:
            video = self.pingpong(video, meta, config.frac_progress)
        if STREAM_TEXT in config.effects:
            video = self.title(video, meta)
        if STREAM_FADE in config.effects:
            video = self.fade(video, config.fade_duration, config.max_duration)
        # if STREAM_CIRCLE in config.effects:
        #     video = self.circle(video, config.circle_mask)
        return video
    
    def mosaic(self, metadata):
        
        config = self.config
        num_videos = len(metadata)
        stream = None
        max_duration = max([meta['QuickTime:Duration'] for meta in metadata])
        print(max_duration)
        
        
        config.fade_duration = 3
        config.max_duration = max_duration
        config.circle_mask = self.load_mask('circle3')
        
        # max_duration=20
        
        
        
        for index,((j,i), meta) in enumerate(zip(self.ji, metadata)):
            
            if index in config.exclude_index:
                continue
            
            x = self.ox + (i*config.width) % config.display_width
            y = self.oy + (j*config.height) % config.display_height
            config.name = 'video_{index}_{i}_{j} '.format(**locals())
            config.frac_progress = index / num_videos
            
            pprint(meta)
            
            # -fflags +genpts -stream_loop -1
            #filter_complex_threads=1, 
            video = (
                ffmpeg
                .input(meta['SourceFile'], stream_loop=-1, t=max_duration, )
                .filter('crop', meta['w'],meta['h'],meta['x'],meta['y'])
                .filter('scale', self.panel_resolution) 
                )
            
            
            video = self.effects(video, config, meta)
                
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
        
        # null = FilterNode(stream, 'nullsrc', max_inputs=1).stream()
        # stream = self.circle(stream, config.circle_mask)
        # stream = ffmpeg.overlay(null, stream)
        
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
    
    def timelapse(self):
        output_filename = self.config.final_pattern.format(**locals())
        
        return (ffmpeg
            .input(self.config.in_pattern+'.jpg', pattern_type='glob', framerate=12)
            .filter('deflicker', mode='pm', size=10)
            .filter('scale', size='hd1080', force_original_aspect_ratio='increase')
            .output(output_filename, crf=20, preset='slower', movflags='faststart', pix_fmt='yuv420p')
            .run()
        )
        
        


def create(config=None):
    '''create movie
    args:
        config
    '''
    
    st = time.time()
    renderer = Renderer(config) 
    
    if config.mode == 'timelapse':
        # Special handling since we can glob the files
        final = renderer.timelapse()
    else:
        raw = config.get_raw()
        metadata = config.get_metadata(raw)
        pprint(metadata[-1])
        
        if config.mode == 'fullscreen':
            final = renderer.concatenate(metadata)
        elif config.mode in ['youtube', 'world']:
            final = renderer.mosaic(metadata)
        else:
            raise KeyError('Missing mode: {}'.format(config.mode))
    
    
    print(final)
    delta = (time.time() - st)/60
    print('Minutes Running: {:0.2f}'.format(delta))


if __name__ == '__main__':
    config = Config()
    create(config)