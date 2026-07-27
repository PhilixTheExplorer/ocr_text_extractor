<p align="center">
  <img src="https://raw.githubusercontent.com/PhilixTheExplorer/lexo/main/src/lexo/assets/lexo.png" alt="Lexo logo" width="120">
</p>

<h1 align="center">Lexo</h1>

<p align="center">
  <a href="https://pypi.org/project/lexo/"><img src="https://img.shields.io/pypi/v/lexo.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/lexo/"><img src="https://img.shields.io/pypi/pyversions/lexo.svg" alt="Python versions"></a>
  <a href="https://pepy.tech/projects/lexo"><img src="https://api.pepy.tech/badge/lexo" alt="Total PyPI downloads"></a>
  <a href="https://github.com/PhilixTheExplorer/lexo/actions/workflows/ci.yml"><img src="https://github.com/PhilixTheExplorer/lexo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/PhilixTheExplorer/lexo/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="License: AGPL-3.0"></a>
</p>

<p align="center">
  <a href="https://github.com/PhilixTheExplorer/lexo/blob/main/README.md">English</a> | <b>မြန်မာ</b>
</p>

**Lexo** (Local EXtraction and OCR) သည် မိမိစက်ထဲတွင်ပင် သီးခြား Run နိုင်သည့် Desktop Document OCR Tool တစ်ခု ဖြစ်ပါသည်။ PDF များနှင့် ဓာတ်ပုံများမှ စာသားများကို ပြင်ဆင်ရလွယ်ကူသည့် Text ဖိုင်အဖြစ် ပြောင်းလဲပေးနိုင်ပြီး၊ အခမဲ့ဖြစ်ကာ တိကျမှုမြင့်မားသည့် Google Docs OCR ကို အသုံးပြုထားသောကြောင့် **မြန်မာစာ (Myanmar script)** အတွက် အထူးကောင်းမွန်စွာ အလုပ်လုပ်ပါသည်။

လုပ်ဆောင်ချက် အများစုသည် မိမိစက်ထဲမှာပင် အလုပ်လုပ်ပါသည်။ Google Docs OCR အသုံးပြုချိန်တွင်သာ အင်တာနက် လိုအပ်မည်ဖြစ်ပြီး၊ မိမိ၏ Google Account ကို တိုက်ရိုက်သုံးသည်ဖြစ်၍ ကုန်ကျစရိတ် လုံးဝ မရှိပါ။ Lexo ကို မြန်မာ OCR အလုပ်များအတွက် အထူးရည်ရွယ်၍ တည်ဆောက်ထားခြင်း ဖြစ်ပါသည် (ဥပမာ စကင်ဖတ်ထားသည့် စာအုပ်များ၊ PDF ဟောင်းများ၊ Dataset ပြင်ဆင်ခြင်းနှင့် EPUB ထုတ်လုပ်ခြင်း စသည့် အင်္ဂလိပ်စာလုံး ဦးစားပေး OCR Tool များ အဆင်မပြေသည့်နေရာများအတွက် အထူးသင့်တော်ပါသည်။) သင့်လျော်သည့် Google Docs OCR Language Hint ပေးလိုက်ပါက အခြား ဘာသာစကားများကိုလည်း OCR ပြုလုပ်နိုင်ပါသည်။

## အဓိက လုပ်ဆောင်ချက်များ

- **မြန်မာစာ ဦးစားပေး OCR Workflow** - OCR Language Hint ၏ မူလတန်ဖိုး (Default) ကို မြန်မာစာ (`my`) ဟု သတ်မှတ်ထားပြီး Unicode Normalization နှင့် မြန်မာ Font ပါဝင်သောကြောင့် ပြန်လည်စစ်ဆေးရာတွင် အဆင်ပြေပါသည်။
- **မိမိ Google Account ဖြင့် အခမဲ့ အသုံးပြုနိုင်ခြင်း** - ငွေပေးရသည့် OCR API များ မလိုဘဲ စာမျက်နှာအလိုက် ကုန်ကျစရိတ်မရှိပါ။ ကြီးမားသည့် Local OCR Model များကိုလည်း ဒေါင်းလုဒ်ဆွဲစရာ မလိုပါ။
- **PDF များကို Batch OCR ပြုလုပ်နိုင်ခြင်း** - ရွေးချယ်ထားသော PDF များ သို့မဟုတ် Folder တစ်ခုလုံးရှိ PDF များကို တစ်ပြိုင်နက် လုပ်ဆောင်ပေးပြီး PDF တစ်ဖိုင်လျှင် UTF-8 TXT ဖိုင်တစ်ခုစီ ထုတ်ပေးပါသည်။ အကြောင်းတစ်ခုခုကြောင့် ရပ်တန့်သွားပါကလည်း ဆက်လက် Run နိုင်ပါသည်။
- **Error Recovery စနစ်** - OCR ပြုလုပ်စဉ် ခဏတာ Error တက်သွားသည့် စာမျက်နှာများကို အလိုအလျောက် Retry ပြုလုပ်ပေးမည်ဖြစ်ပြီး၊ မအောင်မြင်သေးသည့် စာမျက်နှာများကိုလည်း ဖိုင်တစ်ခုလုံး ပြန်လုပ်စရာမလိုဘဲ သီးခြား ပြန်လည် Run နိုင်ပါသည်။
- **PDF ပြင်ဆင်ရေး လုပ်ဆောင်ချက်များ** - စာမျက်နှာ အပိုင်းအခြား ထုတ်ယူခြင်း (Extract)၊ ခွဲထုတ်ခြင်း (Split)၊ ဘောင်ဖြတ်ခြင်း (Crop)၊ လှည့်ခြင်း (Rotate)၊ ပေါင်းစည်းခြင်း (Merge) နှင့် စာမျက်နှာ နှစ်ခုတွဲပါသော Spread များကို သီးခြား စာမျက်နှာများအဖြစ် ခွဲထုတ်နိုင်ခြင်း။
- **GUI Visual Crop နှင့် Split Editor** - စာမျက်နှာပေါ်တွင် Crop Box ဆွဲ၍ ခေါင်းစီးများနှင့် စာမျက်နှာနံပါတ်များကို ဖယ်ရှားနိုင်ပြီး စကင်ဖတ်ထားသော Two-up Spread များကို ခွဲထုတ်နိုင်ပါသည်။
- **Smart OCR Routing** - Digital PDF များရှိ စာသားများကို Text Layer မှ တိုက်ရိုက် ရယူပေးပြီး (အရည်အသွေး ဆုံးရှုံးမှု မရှိဘဲ ချက်ချင်းရရှိသည်) စကင်ဖတ်ထားသော စာမျက်နှာများကိုသာ OCR ပြုလုပ်ပေးပါသည်။
- **Google Docs OCR** - အခမဲ့ဖြစ်ပြီး တိကျမှုမြင့်မားကာ (အထူးသဖြင့် မြန်မာစာအတွက်) မိမိ Google Account ဖြင့် သီးခြား Run မည် ဖြစ်ပါသည်။ `--lang` တန်ဖိုး ပြောင်းလဲ၍ အခြား ဘာသာစကားများကိုလည်း သုံးနိုင်ပါသည်။
- **မြန်မာစာစနစ်နှင့် ကိုက်ညီသည့် စာသားပြင်ဆင်ပေးမှု** - NFC Normalization နှင့် Zero-width space များကို သန့်စင် ထိန်းသိမ်းပေးပါသည်။
- **တိုက်ရိုက် စစ်ဆေး ပြင်ဆင်နိုင်ခြင်း** - Desktop App တွင် စာမျက်နှာတစ်ခုချင်းစီ၏ OCR ထွက်ရှိချက်ကို မူရင်း စာမျက်နှာနှင့် ယှဉ်တွဲပြသပေးသဖြင့် တိုက်ရိုက် စစ်ဆေး ပြင်ဆင်နိုင်ပါသည်။
- **Formats မျိုးစုံဖြင့် ထုတ်ယူနိုင်ခြင်း** - Plain Text (Default)၊ Markdown (YAML Frontmatter ပါဝင်သည်) နှင့် JSONL (NLP / LLM Dataset အလုပ်များအတွက်)။
- **Desktop GUI နှင့် CLI နှစ်မျိုးလုံး ပါဝင်ခြင်း** - Engine တစ်ခုတည်းကို အသုံးပြုထားသည့် GUI နှင့် CLI နှစ်မျိုးလုံး ပါဝင်ပါသည်။

## Install ပြုလုပ်ခြင်း

Lexo သည် Python Package တစ်ခု ဖြစ်ပါသည်။ [uv](https://docs.astral.sh/uv/) ဖြင့် Install ပြုလုပ်နိုင်ပါသည်။

```bash
uv tool install lexo            # `lexo` CLI နှင့် `lexo gui`
```

uv မသုံးလိုပါက အခြား Python Package Manager များကိုလည်း အသုံးပြုနိုင်ပါသည်။

```bash
pipx install lexo
# or
python -m pip install lexo
```

လိုအပ်သည်များ အားလုံး ပါဝင်ပြီးဖြစ်၍ သီးခြား ထပ်မံ ထည့်သွင်းရန် မလိုပါ။

## စတင်အသုံးပြုနည်း

Desktop App ကို ဖွင့်ပါ၊ စာရွက်စာတမ်းဖွင့်ပါ၊ Extract Text သို့မဟုတ် Google Docs OCR ကို ရွေးပါ၊ ရလဒ်ကို စစ်ဆေးပြီး Export ပြုလုပ်ပါ။

```bash
lexo gui
```

CLI တွင် Digital PDF များကို Account မလိုဘဲ တိုက်ရိုက် စာသားထုတ်ယူနိုင်ပါသည်။

```bash
lexo extract report.pdf -o report.txt
```

စကင်ဖတ်ထားသည့် PDF များနှင့် ဓာတ်ပုံများအတွက် Google Docs OCR ကို အသုံးပြုပါသည်။ အောက်ပါ Google Setup ကို တစ်ကြိမ် ပြုလုပ်ထားပြီးပါက Login ဝင်၍ OCR စတင်နိုင်ပါသည်။

```bash
lexo login
lexo ocr scan.pdf --lang my -o scan.txt
```

အခြေခံ PDF ပြင်ဆင်မှုများအတွက် Google Account Login ဝင်ရန် မလိုပါ။

```bash
lexo pdf extract book.pdf --pages "1-3,7,10-" -o subset.pdf
lexo pdf split book.pdf --every 10
lexo pdf crop book.pdf --top 8 --bottom 8 -o trimmed.pdf
```

Command အားလုံးကို ကြည့်ရှုရန် `lexo --help` (သို့မဟုတ် `lexo pdf --help`) ဟု ရိုက်နှိပ်ပါ။

## PDF များကို အစုလိုက် Batch OCR ပြုလုပ်ခြင်း

PDF ဖိုင်များကို တစ်ဖိုင်ချင်း ဖွင့်စရာမလိုဘဲ အများအပြားကို တစ်ပြိုင်နက် OCR ပြုလုပ်ရန် Batch OCR ကို သုံးနိုင်ပါသည်။ Folder တစ်ခု ပေးလိုက်ပါက ၎င်းအတွင်းရှိ PDF အားလုံးကို အလိုအလျောက် OCR ပြုလုပ်ပေးပါမည်။

```bash
lexo login
lexo ocr-batch ./pdfs --out-dir ./txt
```

သတ်မှတ်ထားသည့် PDF ဖိုင်များကိုလည်း သီးခြား ရွေးချယ်ပေးနိုင်ပါသည်။

```bash
lexo ocr-batch chapter-a.pdf chapter-b.pdf --out-dir ./txt
```

Lexo သည် မူရင်း ဖိုင်အမည်ကို ထိန်းသိမ်းထားပြီး Extension ကိုသာ `.txt` သို့ ပြောင်းလဲပေးပါသည်။ ထွက်ရှိပြီးသား TXT ဖိုင်များကို အလိုအလျောက် ကျော်သွားမည်ဖြစ်၍ ရပ်တန့်သွားသည့် Batch အလုပ်များကို ပြန်လည် Run ပါက မပြီးသေးသည့် ဖိုင်များမှ စတင်ပါမည်။ ပြန်လည် အစားထိုးလိုပါက `--overwrite` ထည့်သွင်းပါ။
Batch OCR သည် မူလအားဖြင့် စာမျက်နှာတိုင်းကို ပုံအဖြစ် ပြောင်းလဲ၍ OCR လုပ်ဆောင်ပါသည်။ Embedded Text ကို ထိန်းသိမ်းလိုပါက `--no-force-ocr` ကို အသုံးပြုပါ။

Desktop App တွင် Welcome Screen ရှိ **Batch OCR PDFs** ကို ရွေးပါ၊ သို့မဟုတ် **File -> Batch OCR PDFs...** ကို ဖွင့်ပါ။ PDF တစ်ဖိုင်ချင်း ဖြစ်စေ၊ Folder တစ်ခုလုံး ဖြစ်စေ ထည့်သွင်းနိုင်ပြီး Export ထုတ်မည့် Folder ကို ရွေးချယ်၍ OCR စတင်နိုင်ပါသည်။

## Video Tutorials

Lexo ၏ Setup နှင့် မြန်မာ OCR အသုံးပြုနည်း ဗီဒီယိုများ (~၁ မိနစ်ခန့်စီ)

OCR လုပ်ဆောင်ချိန်သည် အင်တာနက် အမြန်နှုန်းနှင့် Google Drive တုံ့ပြန်ချိန်ပေါ် မူတည်ပါသည်။ လိုင်းနှေး၍ ခဏတာ Error တက်သွားသည့် စာမျက်နှာများကို Lexo မှ အလိုအလျောက် Retry ပြုလုပ်ပေးပါသည်။ မအောင်မြင်သည့် စာမျက်နှာများ ကျန်ရှိနေပါက "Retry Failed Pages" ခလုတ် ပေါ်လာမည်ဖြစ်ပြီး ထိုစာမျက်နှာများကိုသာ သီးခြား ပြန်လည် OCR ပြုလုပ်နိုင်ပါသည်။

### ၁။ uv ဖြင့် Install လုပ်ခြင်းနှင့် Google Cloud Setup ပြုလုပ်ခြင်း

အစပျိုး လိုအပ်ချက်များ - `uv tool install lexo` ဖြင့် Lexo ကို Install လုပ်ခြင်း → Google Cloud Project ဖန်တီးခြင်း → Drive API ဖွင့်ခြင်း → OAuth consent screen ပြင်ဆင်ခြင်း → `credentials.json` ဒေါင်းလုဒ်ဆွဲ၍ Config Directory ထဲသို့ ထည့်ခြင်း → `lexo login` ဖြင့် Login ဝင်ခြင်း။

https://github.com/user-attachments/assets/92d86684-ebaa-438a-a6dd-880d49943405

### ၂။ စကင်ဖတ်ထားသည့် မြန်မာ PDF ကို OCR ပြုလုပ်ခြင်း (GUI)

စကင်ဖတ်ထားသည့် မြန်မာ PDF အတွက် GUI အသုံးပြုနည်း - ဖိုင်ကို ဖွင့်ခြင်း → Visual Editor ဖြင့် **Two-up Spread များကို ခွဲထုတ်ခြင်း** နှင့် ခေါင်းစီး/ဘေးဘောင်များကို **Crop ပြုလုပ်ခြင်း** → **Google Docs OCR run ခြင်း** → စာမျက်နှာအလိုက် စာသား စစ်ဆေးခြင်း → Plain Text အဖြစ် **Export ထုတ်ယူခြင်း**။

https://github.com/user-attachments/assets/b247cdc5-0421-4400-bc6c-f4dc35268268

### ၃။ Non-Unicode Font ဟောင်း PDF များမှ မြန်မာစာသား စစ်မှန်စွာ ရယူခြင်း (GUI)

မြန်မာ စာရွက်စာတမ်း အချို့ကို Win Innwa သို့မဟုတ် Win Myanmar ကဲ့သို့သော Non-Unicode Font ဟောင်းများဖြင့် ရိုက်နှိပ်ထားလေ့ရှိပါသည်။ ၎င်းဖောင့်များသည် ASCII စာလုံးများပေါ်တွင် မြန်မာပုံစံ အစားထိုးပြထားခြင်းဖြစ်၍ PDF ၏ Text Layer ထဲတွင် အင်္ဂလိပ်စာလုံးများသာ ကိန်းဝပ်နေပါသည်။ သို့ဖြစ်၍ ရိုးရိုး Text Extraction ပြုလုပ်ပါက ဖတ်မရသည့် ASCII စာလုံးများသာ ထွက်လာမည် ဖြစ်သည်။

*(မှတ်ချက် - ထိုသို့ ထွက်ရှိလာသည့် ASCII စာလုံးများကို ရိုးရိုး Text Extract ပြုလုပ်ပြီး Win-to-Unicode Font Converter တစ်ခုခုဖြင့် ပြောင်းလဲ၍လည်း မြန်မာ Unicode စာသား ပြန်လည် ရရှိနိုင်ပါသည်။ Google Docs OCR သည် Font Converter သီးခြား သုံးစရာ မလိုဘဲ စာရွက်ပေါ်ရှိ မြန်မာစာလုံးများကို မျက်စိဖြင့် မြင်သည့်အတိုင်း Unicode အဖြစ် တိုက်ရိုက် ပြောင်းလဲပေးသည့် နည်းလမ်းဖြစ်ပါသည်။)*

Lexo GUI တွင် ထိုအခြေအနေမျိုးကို မည်သို့စစ်ဆေးပြီး စစ်မှန်သော မြန်မာ Unicode ပြန်လည်ရရှိရန် Google Docs OCR ဖြင့် မည်သို့ ပြောင်းလဲ OCR လုပ်ရမည်ကို ဤဗီဒီယို၌ ပြသထားပါသည်။

https://github.com/user-attachments/assets/9cd60cbc-6a2b-4925-b076-89e97346e391

## Command များ

| Command | လုပ်ဆောင်ချက် |
|---------|-------------|
| `lexo extract <pdf>` | Digital PDF တစ်ခု၏ Text Layer ကို စာသားအဖြစ် ထုတ်ယူသည် |
| `lexo ocr <pdf\|image>` | စကင်ဖတ်ထားသော စာရွက်စာတမ်းကို OCR ပြုလုပ်သည် (`--lang`, `--force-ocr`) |
| `lexo ocr-batch <files-or-folders> -o <directory>` | PDF များကို အစုလိုက် OCR ပြုလုပ်၍ UTF-8 TXT ဖိုင်များ ထုတ်ပေးသည် |
| `lexo pdf info\|extract\|split\|crop\|rotate\|merge\|split-spread` | PDF ပြင်ဆင်မှု လုပ်ဆောင်ချက်များ |
| `lexo login` / `lexo logout` | Google Account Login / Logout (Token ကို OS Keychain တွင် သိမ်းဆည်းသည်) |
| `lexo gui` | Desktop App ကို ဖွင့်သည် |
| `lexo info` | Lexo Version နှင့် Data သိမ်းဆည်းသည့် လမ်းကြောင်းကို ပြသသည် |
| `lexo check-update` | Version အသစ် ရှိမရှိ PyPI တွင် စစ်ဆေးသည် |

`lexo extract` နှင့် `lexo ocr` တို့တွင် `--format text|markdown|jsonl` ကို အသုံးပြုနိုင်ပါသည်။ Batch OCR သည် Plain Text ကို ထုတ်ပေးပါသည်။

## Google Docs OCR Setup ပြုလုပ်နည်း (တစ်ကြိမ်တည်း)

Lexo ၏ OCR သည် အခမဲ့ဖြစ်ပြီး တိကျမှုမြင့်မားသော Google Docs OCR ကို အသုံးပြုထားပါသည်။ မိမိ၏ Google Account ဖြင့် သီးခြား အလုပ်လုပ်မည် ဖြစ်သဖြင့် ကိုယ်ပိုင် OAuth Client Credentials (`credentials.json`) လိုအပ်ပါသည်။ အောက်ပါ Setup ကို တစ်ကြိမ်သာ ပြုလုပ်ရန် လိုအပ်ပါသည်။

1. **Google Cloud Project ဖန်တီးပါ (သို့မဟုတ် ရှိပြီးသား Project သုံးပါ)** - [Google Cloud Console](https://console.cloud.google.com/) တွင် ပြုလုပ်ပါ။
2. **Google Drive API ကို Enable လုပ်ပါ** - APIs & Services -> Library -> "Google Drive API" ကို ရှာဖွေ၍ Enable ပြုလုပ်ပါ။
3. **OAuth Consent Screen ပြင်ဆင်ပါ** - APIs & Services -> OAuth consent screen -> User Type ကို **External** ရွေးပါ -> App Name နှင့် Email ထည့်ပါ -> **Test users** အောက်တွင် မိမိ၏ Google Email Account ကို ထည့်သွင်းပါ။
4. **OAuth Client ID ဖန်တီးပါ** - APIs & Services -> Credentials -> Create credentials -> OAuth client ID -> Application type ကို **Desktop app** ရွေးပါ -> Create -> **Download JSON** နှိပ်၍ ဖိုင်အမည်ကို `credentials.json` ဟု ပြောင်းပါ။
5. **`credentials.json` ကို အောက်ပါ လမ်းကြောင်းတစ်ခုခုတွင် ထားရှိပါ** -
   - `LEXO_GOOGLE_CREDENTIALS` Environment Variable လမ်းကြောင်း၊ သို့မဟုတ်
   - Lexo Config Directory (`lexo info` တွင် ကြည့်ပါ)၊ သို့မဟုတ်
   - လက်ရှိ Working Directory။
6. **Login ဝင်ပါ** - `lexo login` ကို Run ပါ (GUI တွင် Account -> Sign in with Google)။ Browser ပွင့်လာပါက ခွင့်ပြုချက် ပေးလိုက်ပါ။ Token ကို OS Keychain တွင် လုံခြုံစွာ သိမ်းဆည်းသွားမည် ဖြစ်ပြီး `credentials.json` ကို Login ဝင်ချိန်၌သာ ဖတ်ရှုမည် ဖြစ်ပါသည်။

မှတ်ချက်များ -

- Lexo သည် အနည်းဆုံး လိုအပ်သည့် `drive.file` Scope ကိုသာ တောင်းဆိုသဖြင့် မိမိ သီးခြား ဖန်တီးသည့် ယာယီ ဖိုင်များကိုသာ သုံးစွဲနိုင်မည် ဖြစ်ပါသည်။
- OAuth App သည် **Testing** အဆင့်တွင် ရှိနေပါက Google မှ ရန်ဖန်ရန်ခါ (၇ ရက်ခန့်တွင်) Token သက်တမ်း ကုန်ဆုံးစေတတ်သဖြင့် `lexo login` ကို ပြန်လည် ပြုလုပ်ပေးရန် လိုအပ်နိုင်ပါသည်။
- `lexo logout` (သို့မဟုတ် Account -> Sign out) ဖြင့် အချိန်မရွေး Logout ထွက်နိုင်ပါသည်။

## မြန်မာစာ စနစ်ဆိုင်ရာ မှတ်ချက်များ

- OCR Language Hint ၏ Default တန်ဖိုးမှာ `my` ဖြစ်ပါသည်။ `--lang` ဖြင့် ပြောင်းလဲနိုင်ပါသည်။
- Language Hint သင့်လျော်စွာ ပေးလိုက်ပါက အခြား ဘာသာစကားများကိုလည်း Google Docs OCR မှတစ်ဆင့် ပြောင်းလဲနိုင်ပါသည်။
- ထွက်ရှိလာသည့် စာသားများကို Unicode NFC သို့ Normalize ပြုလုပ်ပေးပြီး Zero-width space များကို သန့်စင် ထိန်းသိမ်းပေးပါသည်။
- မြန်မာ Unicode Font ([Noto Sans Myanmar](https://fonts.google.com/noto/specimen/Noto+Sans+Myanmar), SIL Open Font License) ကို Lexo တွင် တိုက်ရိုက် ထည့်သွင်းပေးထားသဖြင့် စက်ထဲတွင် Font မရှိသော်လည်း GUI ၌ မြန်မာစာ မှန်ကန်စွာ ပေါ်ပါမည်။ License ကို `OFL.txt` အဖြစ် ထည့်သွင်းထားပါသည်။

Lexo ကို ဖန်တီးရသည့် အဓိက အကြောင်းရင်းမှာ အခြား OCR Tool အများစုသည် အင်္ဂလိပ်စာလုံးများအတွက်သာ အဓိက အဆင်ပြေကြသောကြောင့် ဖြစ်ပါသည်။ Tesseract သို့မဟုတ် PaddleOCR ကဲ့သို့ Local Engine များ ရှိသော်လည်း မြန်မာစာ တိကျမှု၊ Setup ပြုလုပ်ရသည့် အရွယ်အစားနှင့် ယုံကြည်စိတ်ချရမှုတို့တွင် ကွာခြားချက် ကြီးမားပါသည်။ Lexo သည် လက်တွေ့ကျပြီး အခမဲ့ အသုံးပြုနိုင်သည့် Google Docs OCR ကို အသုံးပြုထားပြီး၊ အနာဂတ်တွင် အခြား OCR Engine များ ပါဝင်လာစေရန် Provider Architecture ကို တည်ဆောက်ထားပါသည်။

## အနာဂတ် ရည်မှန်းချက်များ

Lexo သည် စကင်ဖတ်ထားသည့် သို့မဟုတ် ဟောင်းနွမ်းနေသည့် မြန်မာ စာရွက်စာတမ်းများကို ပြင်ဆင်ရလွယ်ကူသည့် စာသားအဖြစ် ပြောင်းလဲပေးနိုင်ရန် အဓိက ဦးတည်ထားပါသည်။ Document Layout ကို နားလည်သည့် Text Extraction၊ ဇယား (Table) Structure ခွဲထုတ်ခြင်းနှင့် Semantic Field ရှာဖွေခြင်း စသည့် Document Intelligence Feature များကိုမူ လတ်တလောတွင် မထည့်သွင်းရသေးပါ။ အနာဂတ်တွင် ယုံကြည်စိတ်ချရသည့် အခမဲ့ နည်းလမ်းများ ပေါ်ထွက်လာပါက ထို Feature များကို ဆက်လက် ဖြည့်စွက်သွားမည် ဖြစ်ပါသည်။

## အသုံးပြုထားသည့် နည်းပညာများ

| နယ်ပယ် | နည်းပညာ / Library များ |
|--------|------------|
| Language | Python 3.11+ |
| CLI | [Typer](https://typer.tiangolo.com/) |
| Desktop GUI | [PySide6](https://doc.qt.io/qtforpython/) (Qt) |
| PDF Engine | [PyMuPDF](https://pymupdf.readthedocs.io/) |
| Image Processing | [Pillow](https://pillow.readthedocs.io/en/stable/index.html/) |
| OCR Provider | [Google Drive API](https://developers.google.com/workspace/drive) (Google Docs OCR) |
| Credentials | [keyring](https://github.com/jaraco/keyring) (OS Keychain) |
| Settings | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Logging | [structlog](https://www.structlog.org/) |
| Paths | [platformdirs](https://github.com/tox-dev/platformdirs) |
| Build System | [uv](https://docs.astral.sh/uv/) + [Hatchling](https://hatch.pypa.io/) |
| Code Quality | [Ruff](https://docs.astral.sh/ruff/), [mypy](https://mypy-lang.org/), [pytest](https://docs.pytest.org/) |
| CI/CD | GitHub Actions, PyPI Trusted Publishing |

## Development

```bash
uv sync
uv run ruff check src tests
uv run mypy src/lexo
uv run pytest
```

Architecture ဆိုင်ရာ အသေးစိတ်ကို [docs/ARCHITECTURE.md](https://github.com/PhilixTheExplorer/lexo/blob/main/docs/ARCHITECTURE.md) တွင် ကြည့်ပါ။

## ပါဝင်ကူညီရန် (Contributing)

Bug သတင်းပို့ခြင်း၊ စာရွက်စာတမ်းများ ပြင်ဆင်ပေးခြင်းနှင့် Pull Request များကို ကြိုဆိုပါသည်။ အသေးစိတ်ကို [CONTRIBUTING.md](https://github.com/PhilixTheExplorer/lexo/blob/main/CONTRIBUTING.md) တွင် ကြည့်ပါ။

## License

AGPL-3.0 License အောက်တွင် ထုတ်ဝေထားပါသည်။ [LICENSE](https://github.com/PhilixTheExplorer/lexo/blob/main/LICENSE) တွင် ကြည့်ပါ။
