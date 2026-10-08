```markdown
# **Bloodborne PC (नेचिव लिनक्स पोर्ट) - एन्हांस्ड एडिशन**

*Bloodborne* PC पोर्ट का एक अनुकूलित, नेचिव लिनक्स वर्शन जिसमें C-आधारित कस्टम अचीवमेंट ट्रैकिंग इंजन और एक इंटरैक्टिव कंपेनियन UI लॉन्चर शामिल है।

<img width="1801" height="1009" alt="swappy-20261008_193643" src="https://github.com/user-attachments/assets/73322c34-513e-45d5-9cb0-1c1253ec5bf2" />

---

## **विशेषताएं (Features)**
* **नेचिव लिनक्स परफॉरमेंस:** ऑप्टिमाइज्ड फ्रेम पेसिंग के साथ सीधे Vulkan के माध्यम से चलता है।
* **कस्टम C ट्रॉफी हुक:** वास्तविक समय में मील के पत्थर (milestones) और बॉस की जीत को सटीक रूप से कैप्चर करने के लिए `runtime_services.c` में आंतरिक इंजन कॉल (`sceNpTrophyUnlockTrophy`) को इंटरसेप्ट करता है।
* **JSON सिंक:** अनलॉक किए गए डेटा को स्थानीय JSON फ़ाइल (`achievements.json`) में स्वचालित रूप से लिखता है, जो लॉन्चर के ट्रॉफी प्रोग्रेस ट्रैकर को अपडेट करता है।
* **FSR सपोर्ट:** लिनक्स सिस्टम पर हाई-क्वालिटी रेंडरिंग के लिए टेम्पोरल अपस्केलिंग विकल्प (FSR 3.1, FSR 4, और FSR 4.1.1)।

---

## **आवश्यकताएं (Arch Linux)**
प्रोजेक्ट बनाने से पहले, सुनिश्चित करें कि आवश्यक बिल्ड डिपेंडेंसी इंस्टॉल हैं:
```bash
sudo pacman -S --needed base-devel cmake vulkan-headers glslang zydis xbyak miniz
```

बिल्ड और रन करना

    रिपॉजिटरी क्लोन करें:
    Bash

    git clone [https://github.com/pyL1nx/Bloodborne-PC-native-Enhanced-.git](https://github.com/pyL1nx/Bloodborne-PC-native-Enhanced-.git)
    cd Bloodborne-PC-native-Enhanced-

    इंजन कंपाइल करें:
    Bash

    bash build.sh

    गेम और लॉन्चर लॉन्च करें:
    Bash

    bash launcher/bb-launcher.sh

प्रोजेक्ट संरचना (Project Structure)

    src/ - कोर इंजन संशोधन, जिसमें कस्टम runtime_services.c अचीवमेंट हुक शामिल है।

    launcher/ - ट्रॉफ़ी ट्रैक करने और गेम सेटिंग्स को कॉन्फ़िगर करने के लिए पायथन-आधारित UI।

    tests/ - अचीवमेंट डेटा लॉगिंग के लिए बैकएंड सत्यापन और यूनिट टेस्ट।

लाइसेंस (License)

यह प्रोजेक्ट GNU General Public License v2.0 या इसके बाद के संस्करण के तहत लाइसेंस प्राप्त है। विवरण के लिए LICENSE फ़ाइल देखें।

नोट: इस रिपॉजिटरी में केवल कोड संशोधन शामिल हैं और इसमें कॉपीराइट किए गए गेम एसेट, सिस्टम डंप (CUSA03173), या मालिकाना बाइनरी शामिल नहीं हैं।
