import React, { useState, useRef } from 'react';

/**
 * VideoPlayer - 原生 HTML5 视频播放器
 * 支持自动检测视频方向（横版/竖版）并自适应布局
 */
function VideoPlayer({ url }) {
  const [isPortrait, setIsPortrait] = useState(false);
  const videoRef = useRef(null);

  if (!url) {
    return <div className="video-player-error">No video URL</div>;
  }

  // 检测视频方向
  const handleLoadedMetadata = (e) => {
    const video = e.target;
    const aspectRatio = video.videoWidth / video.videoHeight;
    // 如果宽高比 < 1，说明是竖版视频
    setIsPortrait(aspectRatio < 1);
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: '#000',
      }}
    >
      <video
        ref={videoRef}
        src={url}
        controls
        autoPlay
        onLoadedMetadata={handleLoadedMetadata}
        style={{
          maxWidth: isPortrait ? '400px' : '100%',
          maxHeight: '100%',
          width: isPortrait ? 'auto' : '100%',
          height: isPortrait ? '100%' : 'auto',
          objectFit: 'contain',
        }}
      />
    </div>
  );
}

export default VideoPlayer;
