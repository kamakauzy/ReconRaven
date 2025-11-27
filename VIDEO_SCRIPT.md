# ReconRaven SIGINT Platform - 5 Minute Video Script

## [0:00-0:30] HOOK & INTRO
**Visual: Show the enhanced dashboard with live data**

"Ever wondered what's broadcasting around you right now? This is ReconRaven - a complete SIGINT platform I built to detect, analyze, and locate RF signals. Whether it's your neighbor's garage door opener, amateur radio traffic, or unknown ISM band devices - ReconRaven sees it all."

**Key Points:**
- Built entirely on cheap RTL-SDR dongles (~$30 each)
- Professional-grade SIGINT capabilities
- Zero internet dependency - field deployable


## [0:30-1:30] THE PROBLEM IT SOLVES
**Visual: Show cluttered RF spectrum, then show ReconRaven organizing it**

"The RF spectrum is CHAOS. Thousands of signals competing for airtime. Traditional tools like GQRX or SDR# are great for *listening*, but they don't *hunt*. They don't tell you:
- What's normal vs. anomalous
- What device is transmitting
- WHERE that signal is coming from
- Or automatically log everything for analysis later

ReconRaven was born from real frustration during SIGINT training exercises. We needed something that could:
1. Scan multiple bands simultaneously
2. Automatically identify anomalies
3. Triangulate signal sources using Direction Finding
4. Work in the field with zero connectivity"

**Key Stats to Mention:**
- Scans 650+ frequencies across 2m, 70cm, and ISM bands
- Detects signals 15+ dB above baseline automatically
- Records, analyzes, and identifies devices using AI/ML


## [1:30-2:30] CORE FEATURES WALKTHROUGH
**Visual: Live demo of the dashboard tabs**

**[Show Overview Tab]**
"This is mission control. Four RTL-SDR dongles working in concert:
- SDR #0 and #1 scanning 2-meter amateur band
- SDR #2 on 70cm 
- SDR #3 covering ISM 915MHz garage door openers, sensors, etc.

Real-time power meters show signal strength. The Direction Finding compass? That's the magic. Click any detected signal, and ReconRaven triangulates its bearing using phase-coherent sampling across all four SDRs."

**[Switch to Signals Tab]**
"Every anomaly is a card. Color-coded by band:
- Blue = 2-meter amateur
- Green = 70cm 
- Gold = ISM bands

Filter by band, search by frequency, or show only identified devices. Pin high-priority signals to the top. Click any card for deep analysis."

**[Click a Signal - Show Modal]**
"Here's the detail view:
- Power: -5.2 dBm, 14.9 dB above baseline
- Device: Garage Door Opener (71% confidence)
- IQ recording saved for replay in URH or GQRX
- AI-based device fingerprinting using modulation analysis"


## [2:30-3:30] TECHNICAL DEEP DIVE
**Visual: Show spectrum waterfall and charts**

**[Switch to Spectrum Tab]**
"This is the live waterfall display - real-time FFT visualization. Signals scroll down as they're detected. The power distribution chart shows which frequencies are hot.

Under the hood, ReconRaven uses:
- **pyrtlsdr** for SDR control
- **Baseline scanning**: 3-pass noise floor establishment
- **Anomaly detection**: Statistical analysis (>15 dB delta = anomaly)
- **Concurrent mode**: Multiple SDRs scanning different bands in parallel
- **DF mode**: 4-SDR phase-coherent array for bearing calculation using MUSIC algorithm
- **AI analysis**: Whisper for voice transcription, custom ML for device fingerprinting"

**[Switch to Analysis Tab]**
"The Analysis tab shows identified devices. Every time a signal is recorded, ReconRaven analyzes:
- Modulation type (FM, FSK, OOK, etc.)
- Bit rate
- Preamble patterns
- Matches against a device fingerprint database

Results? We've identified garage door openers, wireless sensors, FRS radios, and amateur FM transmissions - all automatically."


## [3:30-4:15] DIRECTION FINDING DEMO
**Visual: Show compass with bearing arrows**

"Here's where it gets serious. Direction Finding requires 4 synchronized SDRs. ReconRaven samples all four simultaneously, measures phase differences, and calculates bearing.

[Point to compass]
- Red arrow: 907.8 MHz garage door opener at 45° 
- Orange arrow: 146.52 MHz amateur radio at 135°
- Each bearing includes confidence score

In the field, you'd combine multiple bearings from different locations to triangulate the exact source. Perfect for fox hunting, interference tracking, or... let's say 'educational purposes.'"


## [4:15-4:50] EXPORT & PRACTICAL USE
**Visual: Show Export tab, click CSV export**

"Everything is logged. Export tab lets you:
- Download as JSON or CSV for external analysis
- Copy frequency lists to clipboard
- Generate PDF reports (coming soon)

Use cases?
- SIGINT training exercises
- Amateur radio direction finding competitions
- IoT device security audits
- RF interference troubleshooting
- Spectrum monitoring and compliance

The platform is modular. Want to add DMR decoding? P25 trunking? Just plug in the demodulator module."


## [4:50-5:00] CALL TO ACTION & OUTRO
**Visual: Show GitHub repo**

"ReconRaven is open source on GitHub. It's built for RTL-SDR hardware - cheap, accessible, and powerful when used right.

⚠️ Big disclaimer: This is ALPHA software. Not fully tested. Proper RF setup is critical - bad antenna placement = garbage data.

But if you're into SDR, SIGINT, or just curious about the invisible RF world around you... give it a try.

Link in description. Now go find some signals."

---

## VISUAL GUIDANCE

### Key Shots to Capture:
1. **Dashboard overview** (full screen, all stats visible)
2. **SDR status cards** (showing 4 active SDRs with power meters)
3. **Signal list** (scrolling through cards, show filtering)
4. **Signal detail modal** (click 907.8 MHz ISM signal)
5. **DF compass** (with bearing arrows pointing)
6. **Spectrum waterfall** (animated, showing live data)
7. **Export functionality** (click CSV export, show download)
8. **Theme toggle** (show dark/light mode)

### Text Overlays to Add:
- "4x RTL-SDR Dongles = ~$120"
- "650+ Frequencies Scanned"
- "15 dB Anomaly Threshold"
- "Real-time DF Bearing Calculation"
- "Zero Internet Required"
- "Open Source on GitHub"

### B-Roll Ideas:
- Physical RTL-SDR dongles plugged into Raspberry Pi
- Antenna setup (show proper separation for DF)
- Terminal output during baseline scan
- GQRX or URH playing back a recorded IQ file
- GitHub repo page

---

## TONE & DELIVERY NOTES

- **Energy level**: High, enthusiastic - this is cool tech!
- **Pace**: Fast but clear - you have 5 minutes, move with purpose
- **Technical balance**: Don't dumb it down, but explain acronyms first use (SIGINT, DF, ISM, etc.)
- **Credibility**: Mention real testing ("we detected garage door openers at 907.8 MHz")
- **Honesty**: Be upfront about alpha status and RF setup requirements
- **Call to action**: Clear, direct - "Link in description, go try it"

## HASHTAGS FOR DESCRIPTION
#SDR #SIGINT #RTLSDRBlog #HamRadio #RFHacking #OpenSource #Cybersecurity #DirectionFinding #RadioScanning #IoTSecurity #Python #RaspberryPi

---

## OPTIONAL: Extended Version (10 min)
If you want to go longer, add:
- **Live hardware setup walkthrough** (showing 4 SDRs, antenna array)
- **CLI usage demo** (`reconraven.py test freq --freq 146.52`)
- **Database deep dive** (SQLite schema, flattened design)
- **RF environment troubleshooting** (why noise matters)
- **Future roadmap** (DMR, P25, trunking, mobile app)





