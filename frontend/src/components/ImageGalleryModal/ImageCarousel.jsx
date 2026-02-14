import React, { useCallback, useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';

/**
 * ImageCarousel - 图片轮播组件
 *
 * 支持:
 * - 左右箭头切换
 * - 键盘 ← → 导航
 * - 底部圆点指示器
 * - framer-motion 过渡动画
 */
function ImageCarousel({
  images,
  currentIndex,
  onIndexChange,
}) {
  const totalImages = images?.length || 0;

  // 追踪滑动方向：1 = 向右（下一张），-1 = 向左（上一张）
  const [direction, setDirection] = useState(0);
  const prevIndexRef = useRef(currentIndex);

  // 上一张
  const handlePrev = useCallback(() => {
    if (currentIndex > 0) {
      onIndexChange(currentIndex - 1);
    } else {
      // 循环到最后一张
      onIndexChange(totalImages - 1);
    }
  }, [currentIndex, totalImages, onIndexChange]);

  // 下一张
  const handleNext = useCallback(() => {
    if (currentIndex < totalImages - 1) {
      onIndexChange(currentIndex + 1);
    } else {
      // 循环到第一张
      onIndexChange(0);
    }
  }, [currentIndex, totalImages, onIndexChange]);

  // 键盘导航
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlePrev();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNext();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlePrev, handleNext]);

  // 根据 index 变化计算滑动方向
  useEffect(() => {
    const prevIndex = prevIndexRef.current;
    if (currentIndex !== prevIndex) {
      // 计算方向：考虑循环情况
      if (currentIndex === 0 && prevIndex === totalImages - 1) {
        // 从最后一张循环到第一张 → 向右
        setDirection(1);
      } else if (currentIndex === totalImages - 1 && prevIndex === 0) {
        // 从第一张循环到最后一张 → 向左
        setDirection(-1);
      } else {
        // 正常情况
        setDirection(currentIndex > prevIndex ? 1 : -1);
      }
      prevIndexRef.current = currentIndex;
    }
  }, [currentIndex, totalImages]);

  if (!images || images.length === 0) {
    return (
      <div className="image-carousel-empty">
        <span className="material-symbols-outlined text-4xl text-text-muted">
          image_not_supported
        </span>
        <p className="text-text-muted text-sm mt-2">No images available</p>
      </div>
    );
  }

  // 动画变体
  const slideVariants = {
    enter: (direction) => ({
      x: direction > 0 ? 300 : -300,
      opacity: 0,
    }),
    center: {
      x: 0,
      opacity: 1,
    },
    exit: (direction) => ({
      x: direction < 0 ? 300 : -300,
      opacity: 0,
    }),
  };

  return (
    <div className="image-carousel">
      {/* 图片容器 */}
      <div className="image-carousel-container">
        <AnimatePresence initial={false} mode="wait" custom={direction}>
          <motion.img
            key={currentIndex}
            src={images[currentIndex]}
            alt={`Image ${currentIndex + 1} of ${totalImages}`}
            className="image-carousel-image"
            variants={slideVariants}
            custom={direction}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{
              x: { type: 'spring', stiffness: 300, damping: 30 },
              opacity: { duration: 0.2 },
            }}
            draggable={false}
          />
        </AnimatePresence>
      </div>

      {/* 左右箭头 - 仅多于1张时显示 */}
      {totalImages > 1 && (
        <>
          <button
            onClick={handlePrev}
            className="image-carousel-arrow image-carousel-arrow-left"
            aria-label="Previous image"
          >
            <ChevronLeft size={24} />
          </button>
          <button
            onClick={handleNext}
            className="image-carousel-arrow image-carousel-arrow-right"
            aria-label="Next image"
          >
            <ChevronRight size={24} />
          </button>
        </>
      )}

      {/* 底部圆点指示器 - 仅多于1张时显示 */}
      {totalImages > 1 && (
        <div className="image-carousel-dots">
          {images.map((_, index) => (
            <button
              key={index}
              onClick={() => onIndexChange(index)}
              className={`image-carousel-dot ${
                index === currentIndex ? 'active' : ''
              }`}
              aria-label={`Go to image ${index + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default ImageCarousel;
