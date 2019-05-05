RES:=1920x1080
X_HALF:=960
Y_HALF:=540
RES_HALF:=960x540


run:
	python run.py


single:
	ffmpeg \
		-i /Volumes/photo/_worlds/DJI_0586.MP4 \
		-i /Volumes/photo/_worlds/DJI_0572.MP4 \
		-i /Volumes/photo/_worlds/DJI_0566.MP4 \
		-i /Volumes/photo/_worlds/DJI_0573.MP4 \
		-filter_complex " \
			nullsrc=size=$(RES) [base]; \
			[0:v] setpts=PTS-STARTPTS, scale=$(RES_HALF) [upperleft]; \
			[1:v] setpts=PTS-STARTPTS, scale=$(RES_HALF) [upperright]; \
			[2:v] setpts=PTS-STARTPTS, scale=$(RES_HALF) [lowerleft]; \
			[3:v] setpts=PTS-STARTPTS, scale=$(RES_HALF) [lowerright]; \
			[base][upperleft] overlay=shortest=1 [tmp1]; \
			[tmp1][upperright] overlay=shortest=1:x=$(X_HALF) [tmp2]; \
			[tmp2][lowerleft] overlay=shortest=1:y=$(Y_HALF) [tmp3]; \
			[tmp3][lowerright] overlay=shortest=1:x=$(X_HALF):y=$(Y_HALF) " \
		-c:v libx264 output.mkv



#

# ffmpeg \
# 	-i 1.avi -i 2.avi -i 3.avi -i 4.avi \
# 	-filter_complex "
# 		nullsrc=size=640x480 [base];
# 		[0:v] setpts=PTS-STARTPTS, scale=320x240 [upperleft];
# 		[1:v] setpts=PTS-STARTPTS, scale=320x240 [upperright];
# 		[2:v] setpts=PTS-STARTPTS, scale=320x240 [lowerleft];
# 		[3:v] setpts=PTS-STARTPTS, scale=320x240 [lowerright];
# 		[base][upperleft] overlay=shortest=1 [tmp1];
# 		[tmp1][upperright] overlay=shortest=1:x=320 [tmp2];
# 		[tmp2][lowerleft] overlay=shortest=1:y=240 [tmp3];
# 		[tmp3][lowerright] overlay=shortest=1:x=320:y=240
# 	"
# 	-c:v libx264 output.mkv

