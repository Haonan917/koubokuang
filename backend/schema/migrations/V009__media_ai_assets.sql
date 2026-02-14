-- ============================================================================
-- V009: Media AI Assets (voice clone / avatar / tts / lipsync)
-- ============================================================================

CREATE TABLE IF NOT EXISTS media_ai_voice_clones (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    voice_id VARCHAR(128) NOT NULL COMMENT 'Voicv voice_id',
    title VARCHAR(255) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    source_type VARCHAR(50) DEFAULT NULL,
    source_url TEXT DEFAULT NULL,
    sample_audio_url TEXT DEFAULT NULL,
    full_audio_url TEXT DEFAULT NULL,
    full_audio_path TEXT DEFAULT NULL,
    clip_audio_url TEXT DEFAULT NULL,
    clip_audio_path TEXT DEFAULT NULL,
    expression_profile JSON DEFAULT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_user_voice (user_id, voice_id),
    INDEX idx_user_created (user_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='语音克隆记录';

CREATE TABLE IF NOT EXISTS media_ai_avatars (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    avatar_id VARCHAR(128) NOT NULL COMMENT 'Avatar ID',
    title VARCHAR(255) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    source_type VARCHAR(50) DEFAULT NULL,
    source_url TEXT DEFAULT NULL,
    full_video_url TEXT DEFAULT NULL,
    full_video_path TEXT DEFAULT NULL,
    clip_video_url TEXT DEFAULT NULL,
    clip_video_path TEXT DEFAULT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_user_avatar (user_id, avatar_id),
    INDEX idx_user_created (user_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='形象克隆记录';

CREATE TABLE IF NOT EXISTS media_ai_tts_results (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    voice_id VARCHAR(128) DEFAULT NULL,
    text LONGTEXT DEFAULT NULL,
    tagged_text LONGTEXT DEFAULT NULL,
    audio_url TEXT DEFAULT NULL,
    original_audio_url TEXT DEFAULT NULL,
    format VARCHAR(20) DEFAULT NULL,
    speed DECIMAL(6, 3) DEFAULT NULL,
    emotion VARCHAR(50) DEFAULT NULL,
    tone_tags JSON DEFAULT NULL,
    effect_tags JSON DEFAULT NULL,
    sentence_emotions JSON DEFAULT NULL,
    auto_emotion TINYINT DEFAULT NULL,
    auto_breaks TINYINT DEFAULT NULL,
    voice_profile JSON DEFAULT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_voice_created (voice_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='文本转语音结果';

CREATE TABLE IF NOT EXISTS media_ai_lipsync_results (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    generation_id VARCHAR(128) DEFAULT NULL,
    model VARCHAR(64) DEFAULT NULL,
    status VARCHAR(32) DEFAULT NULL,
    output_url TEXT DEFAULT NULL,
    video_url TEXT DEFAULT NULL,
    audio_url TEXT DEFAULT NULL,
    video_source_type VARCHAR(50) DEFAULT NULL,
    audio_source_type VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_user_generation (user_id, generation_id),
    INDEX idx_user_created (user_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='对口型生成记录';
