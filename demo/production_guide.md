# Video Production Guide

## Overview

This guide provides comprehensive instructions for recording and editing the Forklift hackathon demo video, ensuring professional quality and effective demonstration of both the tool and Kiro development process.

---

## Pre-Production Setup

### Recording Environment

#### Hardware Requirements
- **Computer**: MacBook M4 or equivalent with sufficient processing power
- **Microphone**: Professional USB microphone or high-quality headset
- **Lighting**: Natural light or soft LED lighting to illuminate screen clearly
- **Backup Storage**: External drive for raw footage and project files

#### Software Requirements
- **Screen Recording**: QuickTime Player (macOS) or OBS Studio (cross-platform)
- **Video Editing**: Final Cut Pro, Adobe Premiere Pro, or DaVinci Resolve
- **Audio Editing**: Audacity or built-in editing tools
- **Terminal**: iTerm2 or Terminal.app with optimized settings

### Terminal Configuration

```bash
# Optimal terminal settings for recording
export TERM=xterm-256color
export COLUMNS=120
export LINES=30

# Font settings (adjust in terminal preferences)
# Font: SF Mono or Monaco
# Size: 14pt (readable at 1080p)
# Theme: Dark theme with high contrast
# Cursor: Visible but not distracting
```

### Environment Variables

```bash
# Required for demo
export GITHUB_TOKEN=your_github_token_here

# Optional for consistent output
export FORKLIFT_CONFIG_PATH=demo/vscode-demo-config.yaml
export FORKLIFT_CACHE_DIR=demo/cache
```

---

## Recording Guidelines

### Video Specifications

#### Technical Settings
- **Resolution**: 1920x1080 (1080p) minimum
- **Frame Rate**: 30 fps (smooth for screen recording)
- **Format**: MP4 (H.264 codec for compatibility)
- **Bitrate**: 8-10 Mbps for high quality
- **Audio**: 48kHz, 16-bit minimum

#### Screen Recording Setup
- **Recording Area**: Full screen or focused terminal window
- **Cursor**: Visible and appropriately sized
- **Notifications**: Disabled during recording
- **Desktop**: Clean, minimal background
- **Menu Bar**: Hidden or minimal items

### Audio Recording

#### Microphone Setup
- **Distance**: 6-8 inches from mouth
- **Environment**: Quiet room with minimal echo
- **Test Recording**: Always test audio levels before main recording
- **Backup**: Record audio separately as backup if possible

#### Narration Guidelines
- **Pace**: 150-160 words per minute (natural speaking pace)
- **Tone**: Professional but enthusiastic
- **Clarity**: Clear pronunciation, avoid filler words
- **Timing**: Synchronize with screen actions

### Recording Process

#### Pre-Recording Checklist
- [ ] Terminal configured with optimal settings
- [ ] Demo environment prepared and tested
- [ ] GitHub token verified and rate limits checked
- [ ] Screen recording software configured
- [ ] Audio input tested and levels set
- [ ] Notifications disabled
- [ ] Clean desktop and terminal
- [ ] Demo scripts and configurations ready

#### Recording Segments

**Segment 1: Tool Demonstration (90 seconds)**
1. **Repository Overview** (15 seconds)
   - Clear command typing
   - Pause for output to display
   - Highlight key statistics

2. **Fork Discovery** (20 seconds)
   - Smooth command execution
   - Allow time for table to render
   - Cursor movement to highlight important data

3. **Commit Analysis** (25 seconds)
   - Execute command with confidence
   - Pause on AI explanations
   - Show variety of commit types

4. **Report Generation** (30 seconds)
   - Command execution
   - Show progress indicators
   - Display final results

**Segment 2: Kiro Development Showcase (60 seconds)**
1. **Spec Creation** (15 seconds)
   - Show requirements document
   - Highlight iterative refinement

2. **Design Process** (15 seconds)
   - Display architecture decisions
   - Show design evolution

3. **Task Implementation** (15 seconds)
   - Show task breakdown
   - Demonstrate TDD process

4. **Evolution Timeline** (15 seconds)
   - Show spec progression
   - Highlight systematic development

**Segment 3: Results & Impact** (30 seconds)
1. **Project Statistics** (10 seconds)
   - Show completion metrics
   - Highlight quality measures

2. **Call to Action** (20 seconds)
   - Repository and PyPI links
   - Encourage exploration

---

## Post-Production Editing

### Video Editing Workflow

#### Import and Organization
1. **Import Footage**: Import all recorded segments
2. **Create Project**: Set up project with 1080p timeline
3. **Organize Clips**: Label and organize by segment
4. **Sync Audio**: Align audio with video if recorded separately

#### Editing Process

**Timeline Structure:**
```
Video Track 1: Main screen recording
Video Track 2: Text overlays and annotations
Audio Track 1: Narration
Audio Track 2: Background music (subtle, if any)
```

**Editing Steps:**
1. **Rough Cut**: Arrange clips in sequence according to script
2. **Timing Adjustment**: Trim clips to match narration timing
3. **Transitions**: Add smooth transitions between segments
4. **Text Overlays**: Add key information and annotations
5. **Color Correction**: Ensure consistent screen brightness
6. **Audio Mixing**: Balance narration and any background elements

#### Visual Enhancements

**Text Overlays and Annotations:**
- Repository URLs and statistics
- Key command highlights
- Important output explanations
- Transition indicators

**Cursor Highlighting:**
- Subtle cursor highlighting for important actions
- Zoom effects for detailed information
- Smooth cursor movement between elements

**Screen Annotations:**
- Arrows pointing to key information
- Boxes highlighting important sections
- Fade-in/fade-out for explanatory text

### Audio Post-Production

#### Audio Enhancement
- **Noise Reduction**: Remove background noise and hum
- **EQ Adjustment**: Enhance voice clarity
- **Compression**: Even out audio levels
- **Normalization**: Consistent volume throughout

#### Synchronization
- **Lip Sync**: Ensure audio matches screen actions
- **Timing**: Adjust for natural pauses and emphasis
- **Transitions**: Smooth audio transitions between segments

---

## Quality Assurance

### Technical Quality Checklist

#### Video Quality
- [ ] Resolution is 1080p or higher
- [ ] Frame rate is consistent (30fps)
- [ ] No dropped frames or stuttering
- [ ] Screen text is clearly readable
- [ ] Colors are accurate and consistent
- [ ] No visual artifacts or compression issues

#### Audio Quality
- [ ] Clear, professional narration
- [ ] No background noise or echo
- [ ] Consistent volume levels
- [ ] Good synchronization with video
- [ ] No audio clipping or distortion

#### Content Quality
- [ ] All demo commands execute successfully
- [ ] Real data demonstrates tool value
- [ ] Kiro development process clearly explained
- [ ] Timing matches script requirements (3 minutes)
- [ ] Professional presentation throughout

### Content Review Checklist

#### Tool Demonstration
- [ ] Problem clearly stated and solution demonstrated
- [ ] Real repositories with compelling examples
- [ ] Smooth command execution without errors
- [ ] Clear output formatting and results
- [ ] Value proposition clearly communicated

#### Kiro Development Showcase
- [ ] Spec-driven development process explained
- [ ] Concrete examples of requirements → implementation
- [ ] Iterative improvement demonstrated
- [ ] Sophisticated development practices shown
- [ ] AI-assisted development benefits highlighted

#### Overall Presentation
- [ ] Professional quality throughout
- [ ] Engaging narrative maintains interest
- [ ] Technical accuracy verified
- [ ] Appropriate pacing and timing
- [ ] Clear call-to-action

---

## Export and Distribution

### Export Settings

#### Video Export
```
Format: MP4 (H.264)
Resolution: 1920x1080
Frame Rate: 30fps
Bitrate: 8-10 Mbps (VBR)
Audio: AAC, 48kHz, 256kbps
```

#### Quality Verification
- **Test Playback**: Verify on different devices
- **File Size**: Ensure reasonable size for upload
- **Compatibility**: Test with various players
- **Backup**: Create multiple quality versions

### File Management

#### File Organization
```
demo/
├── raw_footage/
│   ├── segment1_tool_demo.mov
│   ├── segment2_kiro_showcase.mov
│   └── audio_narration.wav
├── project_files/
│   ├── forklift_demo.fcpx
│   └── assets/
├── exports/
│   ├── forklift_demo_final.mp4
│   ├── forklift_demo_720p.mp4
│   └── forklift_demo_preview.mp4
└── assets/
    ├── thumbnails/
    └── overlays/
```

#### Backup Strategy
- **Local Backup**: External drive with all project files
- **Cloud Backup**: Upload to secure cloud storage
- **Version Control**: Keep multiple export versions
- **Archive**: Preserve raw footage and project files

---

## Troubleshooting

### Common Recording Issues

#### Technical Problems
**Issue**: Screen recording stutters or drops frames
**Solution**: 
- Close unnecessary applications
- Use dedicated recording software (OBS Studio)
- Record in segments if necessary
- Check available disk space

**Issue**: Audio out of sync with video
**Solution**:
- Record audio separately and sync in post
- Use consistent frame rate throughout
- Check audio buffer settings
- Test sync before main recording

**Issue**: Terminal output formatting issues
**Solution**:
- Verify terminal size settings (120x30)
- Test all commands before recording
- Use consistent font and theme
- Check output with different terminal widths

#### Content Problems
**Issue**: Demo commands fail or timeout
**Solution**:
- Use pre-warmed cache
- Have backup pre-recorded outputs
- Test all commands immediately before recording
- Monitor GitHub API rate limits

**Issue**: Narration timing doesn't match actions
**Solution**:
- Practice with timer before recording
- Record narration separately for better control
- Use editing to adjust timing
- Add pauses in script for complex outputs

### Emergency Procedures

#### Live Demo Failures
1. **Have pre-recorded outputs ready** as backup
2. **Switch to alternative repository** (FastAPI instead of VSCode)
3. **Use static screenshots** if commands fail
4. **Continue with Kiro showcase** even if tool demo has issues

#### Technical Failures
1. **Multiple recording attempts** with different settings
2. **Segment recording** if full recording fails
3. **Audio-only backup** if video fails
4. **Screen capture alternatives** (screenshots + narration)

---

## Success Metrics

### Technical Success
- [ ] Video meets all technical specifications
- [ ] Audio is clear and professional quality
- [ ] All demo commands execute successfully
- [ ] Timing matches script requirements exactly
- [ ] Professional presentation quality throughout

### Content Success
- [ ] Tool capabilities clearly demonstrated
- [ ] Real-world value proposition evident
- [ ] Kiro development process well explained
- [ ] Sophisticated AI-assisted development shown
- [ ] Compelling narrative maintains engagement

### Distribution Success
- [ ] Video uploaded successfully to platform
- [ ] Metadata and descriptions optimized
- [ ] Thumbnail is engaging and professional
- [ ] Video is publicly accessible to judges
- [ ] Backup copies available if needed

This comprehensive production guide ensures a professional, compelling demo video that effectively showcases both Forklift's capabilities and the sophisticated use of Kiro in its development.