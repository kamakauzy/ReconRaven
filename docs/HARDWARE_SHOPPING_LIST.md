# ReconRaven Hardware Shopping List

Complete parts list with links and notes for building your ReconRaven system.

---

## 🎯 Recommended Build: Portable Touchscreen System

**Total Cost:** ~$621 | **Assembly Time:** 2 hours | **Field Runtime:** 4-5 hours

### Core Components

| Item | Qty | Price | Link | Notes |
|------|-----|-------|------|-------|
| **Raspberry Pi 5 (16GB)** | 1 | $132 | [CanaKit](https://www.canakit.com/raspberry-pi-5-16gb.html) | 16GB for GUI + 4 SDRs |
| **Official 7" Touchscreen** | 1 | $83 | [Adafruit](https://www.adafruit.com/product/2718) | 800x480 capacitive |
| **SmartiPi Touch 2 Case** | 1 | $43 | [SmartiPi](https://smarticase.com/products/smartipi-touch-2) | Integrates Pi + display |
| **45W USB-C Power Supply** | 1 | $16 | [CanaKit](https://www.canakit.com/raspberry-pi-5-power-supply.html) | Official Pi 5 PSU |
| **256GB microSD (A2 Class)** | 1 | $25 | [Amazon](https://amazon.com/s?k=sandisk+256gb+a2) | Samsung/SanDisk A2 |

### SDR & RF Components

| Item | Qty | Price | Link | Notes |
|------|-----|-------|------|-------|
| **RTL-SDR Blog V4** | 4 | $160 | [RTL-SDR.com](https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/) | $40 each, bias-tee |
| **Nagoya NA-771 Antenna** | 4 | $84 | [Amazon](https://amazon.com/s?k=nagoya+na-771) | $21 each, 2m/70cm |
| **RSHTECH 4-Port Powered Hub** | 1 | $18 | [Amazon](https://amazon.com/dp/B07MQDJLSF) | 5V/4A for SDRs |
| **USB to Barrel Cable (2pk)** | 1 | $5 | [Amazon](https://amazon.com/s?k=usb+barrel+cable) | Hub battery power |

### Positioning & Power

| Item | Qty | Price | Link | Notes |
|------|-----|-------|------|-------|
| **VK-162 USB GPS Dongle** | 1 | $25 | [Amazon](https://amazon.com/dp/B078Y52FGQ) | U-blox chipset |
| **Power Bank (25,000 mAh)** | 1 | $35 | [Amazon](https://amazon.com/s?k=anker+25000) | USB-PD for Pi + hub |

### Optional Accessories

| Item | Qty | Price | Notes |
|------|-----|-------|-------|
| **Active Cooling Fan** | 1 | $8 | For Pi 5, prevents throttling |
| **USB Extension Cables (6ft)** | 4 | $12 | Reduce RF interference |
| **Ferrite Cores** | 10 | $10 | Snap-on, for USB cables |
| **Velcro Strips** | 1 | $8 | Mount hub/GPS to case |

**Optional Total:** $38

---

## 💰 Budget Build: Mobile Single-SDR

**Total Cost:** ~$221 | **Assembly Time:** 30 min | **Field Runtime:** 8+ hours

| Item | Qty | Price | Link |
|------|-----|-------|------|
| Raspberry Pi 5 (8GB) | 1 | $80 | [CanaKit](https://www.canakit.com/raspberry-pi-5-8gb.html) |
| RTL-SDR Blog V4 | 1 | $40 | [RTL-SDR.com](https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/) |
| Nagoya NA-771 | 1 | $21 | [Amazon](https://amazon.com/s?k=nagoya+na-771) |
| VK-162 GPS Dongle | 1 | $25 | [Amazon](https://amazon.com/dp/B078Y52FGQ) |
| 256GB microSD (A2) | 1 | $25 | [Amazon](https://amazon.com/s?k=sandisk+256gb+a2) |
| 20,000 mAh Power Bank | 1 | $30 | [Amazon](https://amazon.com/s?k=anker+20000) |

**Note:** Runs headless (SSH access only). No touchscreen.

---

## 🎯 Direction Finding Array Add-Ons

If building for direction finding (4-SDR phase-coherent):

| Item | Qty | Price | Notes |
|------|-----|-------|-------|
| **3D Printed V-Dipole Mounts** | 4 | $0 | Files: `docs/3d_models/` |
| **RG174 Coax (50Ω, 1m)** | 4 | $20 | Equal length cables |
| **SMA Male Connectors** | 8 | $8 | For custom cables |
| **PVC Frame (0.5m square)** | 1 | $15 | 1/2" PVC pipe + fittings |

**DF Total:** +$43 (assuming 3D printer access)

---

## 📦 What You Already Have (Probably)

- USB keyboard/mouse (for initial setup)
- HDMI cable (if using external monitor during setup)
- Laptop/PC (for initial SD card flashing)
- Multitool/screwdrivers (for case assembly)

---

## 🛒 Where to Buy

### Authorized Retailers

**Raspberry Pi:**
- CanaKit (USA): https://www.canakit.com
- Adafruit (USA): https://www.adafruit.com
- The Pi Hut (UK): https://thepihut.com
- Core Electronics (AUS): https://core-electronics.com.au

**RTL-SDR Blog V4:**
- RTL-SDR.com (Direct): https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/
- Amazon: Search "RTL-SDR Blog V4"

**Antennas:**
- Amazon: Most reliable for Nagoya clones
- HRO (Ham Radio Outlet): Authentic Nagoya
- DX Engineering: Ham radio gear

### International Shipping

**USA:** 2-5 day delivery on most items  
**UK/EU:** Add ~$50 for Pi 5 import, 7-14 days  
**AUS:** Add ~$70, 10-20 days  
**Worldwide:** AliExpress for budget alternatives (30-60 days)

---

## ⚠️ Warnings & Tips

### Don't Cheap Out On:

1. **microSD Card** - A2 speed class is critical! Slow SD = system hangs
2. **Power Supply** - Use official Pi 5 PSU or equivalent 45W USB-PD
3. **RTL-SDR V4** - Don't buy V3 or knock-offs. V4 has better performance.

### Can Save Money On:

1. **Antennas** - Nagoya clones work fine for testing
2. **GPS** - Any U-blox based USB GPS works (VK-162 is just popular)
3. **Power Bank** - Generic brands OK if USB-PD capable

### Compatibility Notes:

- **Pi 4 vs Pi 5**: Pi 4 (8GB) works but slower. Save $20-30.
- **RTL-SDR V3 vs V4**: V4 has bias-tee, better ADC. Worth $5 extra.
- **3rd Party Touchscreens**: Usually work, but official display is guaranteed compatible.

---

## 📊 Cost Comparison

| Configuration | Cost | Runtime | Use Case |
|---------------|------|---------|----------|
| Budget (1 SDR) | ~$221 | 8+ hrs | Mobile recon, learning |
| Recommended (4 SDR + Touch) | ~$621 | 4-5 hrs | Field ops, training |
| DF Array (+$43) | ~$664 | 4-5 hrs | Direction finding |
| PC Development (4 SDR) | ~$200 | N/A | Software dev, testing |

---

## 🔧 Assembly Tools Needed

- Phillips screwdriver (small)
- Tweezers (for ribbon cable)
- Wire strippers (if building custom cables)
- 3D printer access (for DF mounts)
- Patience

---

## 📅 Availability Check (as of Dec 2024)

**In Stock:**
- ✅ Raspberry Pi 5 (all variants)
- ✅ Official Touchscreen
- ✅ RTL-SDR Blog V4
- ✅ Nagoya NA-771

**Limited Stock:**
- ⚠️ SmartiPi Touch 2 Case (check website)

**Backorder:**
- ❌ (None currently)

---

## 🎁 Already Have Some Parts?

### If you have a Pi 4 (8GB):

Still works! Expect:
- Slower boot (~30s vs 15s)
- Reduced performance with 4 SDRs
- Whisper transcription ~50% slower

### If you have generic USB GPS:

Works if it's U-blox based. Test with:
```bash
sudo apt install gpsd gpsd-clients
cgps -s
```

### If you have older RTL-SDR dongles:

V3 works but lacks bias-tee. R820T2 tuner minimum.

---

## 📞 Support

**Questions about parts?**
- Check main README.md
- Open GitHub issue
- RTL-SDR community forums

**Bulk orders (10+ systems)?**
- Contact Raspberry Pi for education pricing
- RTL-SDR.com offers volume discounts

---

**Ready to order?** 

**Total for recommended build: ~$621**

**Add to cart, wait 3-7 days for delivery, and you'll be scanning RF in a weekend!** 🚀

