# FileFlows Real Image (archived)

[![Status: Archived](https://img.shields.io/badge/status-archived-red)](#why-this-project-is-archived)
[![License: EUPL 1.2](https://img.shields.io/badge/License-EUPL%201.2-blue.svg)](LICENSE)

> [!WARNING]
> **This project is archived.** The published images have been deleted from `ghcr.io`, and nothing will be built again. I have stopped using FileFlows and no longer want anything to do with it. The reasons are below.

---

## Why this project is archived

In short:

1. **FileFlows makes telemetry mandatory for free users.** The only way to turn it off is to pay.
2. **FileFlows calls the telemetry "completely anonymous", but its own public code sent a permanent ID for each installation.**
3. **Your "consent" is hidden in a licence agreement that only exists inside the app.** You cannot read it before installing, and there is no separate choice.
4. **You can't tell who you are dealing with.** The EULA names only "FileFlows", which is not a company. fileflows.com has no imprint, no terms, no address and no usable privacy policy.
5. **The website itself tracks visitors without asking.**

In my view, this is not compatible with EU data protection and consumer law. I am filing a complaint with an EU data protection authority, and I am done with FileFlows.

Everything below is sourced. Pages were retrieved on **28 September 2026** unless another date is given.

---

### 1. Telemetry you can only switch off by paying

The FileFlows documentation for the General settings page says:

> **Opting Out:** Anonymous telemetry is required for the free tier to help us sustainably maintain and improve the software. The option to completely disable telemetry is available as a benefit for users with an active license.
>
> — [fileflows.com/docs/webconsole/config/settings/general](https://fileflows.com/docs/webconsole/config/settings/general)

The switch was quietly moved behind the paywall two years before this sentence appeared. It happened in April 2024, in the same commit that introduced the EULA ([`98d2d37`](https://github.com/martinkeat/FileFlows/commit/98d2d3729cef90b7faaf9878787835023ba18d5d), *"FF-1057 - eula / initial config done"*):

```diff
-            if (settings?.DisableTelemetry == true)
+            if (settings?.DisableTelemetry == true && LicenseHelper.IsLicensed())
```

The [24.04 release notes](https://fileflows.com/docs/versions) mention only *"Created an Initial Configuration page which includes an EULA to accept"*. They don't mention that free users could no longer switch telemetry off. Every archived copy of the docs page from April 2025 to 12 May 2026 ([latest capture](https://web.archive.org/web/20260512130010/https://fileflows.com/docs/webconsole/config/settings/general)) still describes telemetry with no free-tier condition. The pricing page does not mention telemetry at all to this day, so what free users are paying with is not listed anywhere they would decide to buy.

| Date | What happened |
| :--- | :--- |
| Jan 2022 | The developer: *"Unless people turned off telemetry and my numbers for additional nodes are wrong."* Anyone could turn it off. ([source](https://reddit.com/r/FileFlows/comments/sbdab6/version_033522/)) |
| Aug 2023 | The developer, after users asked for opt-in: *"I plan to add a starting licensed page/EULA … And I'll have a option to opt in/out from telemetry there."* ([source](https://reddit.com/r/selfhosted/comments/15jledo/fileflows_self_hosted_file_processing_videos/jv24l2o/)) |
| Apr 2024 | Version 24.04 ships that setup page with an EULA but **no** telemetry choice. The same commit makes the opt-out licence-only. The release notes are silent about it. |
| Aug 2025 | The developer: *"If you're using the paid version, you can turn it off. In the free version, it's just part of how it works."* ([source](https://reddit.com/r/selfhosted/comments/1ms1q9x/fileflows_update_25083_now_limits_nodes_in_free/n9324xm/)) |
| May–Sep 2026 | The docs finally state that telemetry is *"required for the free tier"*. |

### 2. "Completely anonymous"?

FileFlows describes the data like this:

- The docs say: *"All data is completely anonymous"*. They also give what they call *"the exact list of anonymous data points sent by the app"*: version, language, deployment method, database type, host OS, architecture, CPU/hardware specifications, number of agents and their hardware, flow element and script usage, and file and storage counts.
- The in-app help text (`i18n/en.json`, key `Telemetry-Help`) says: *"No information about your files or identify information is sent."*
- The in-app EULA says the data *"may include but is not limited to"* a longer list, which adds flow templates, library templates and DockerMods. So the "exact list" in the docs is not exact.

FileFlows' source code was public on GitHub until at least mid-2024, and copies still exist. From the first telemetry code in November 2021 to the latest public copy from July 2024, it sent a **permanent per-installation ID** with every report ([July 2024 copy](https://github.com/martinkeat/FileFlows/blob/645263a992f652e1800154e3e0dcc9133ad9b7d5/Server/Workers/TelemetryReporter.cs#L29-L35)):

```csharp
if (settings.DisableTelemetry == true && LicenseHelper.IsLicensed())
    return; // they have turned it off, dont report anything

TelemetryData data = new TelemetryData();
data.ClientUid = settings.Uid;
...
string url = Globals.FileFlowsDotComUrl + "/api/telemetry";
```

Neither the "exact list" nor the EULA mentions any identifier. Every report also reaches fileflows.com from the user's IP address. A stable ID plus an IP address plus a hardware profile of someone's home server is not what I call anonymous.

### 3. Consent hidden in a licence agreement you cannot read beforehand

Since version 24.04, FileFlows shows an EULA on its first-run setup screen. The rest of the setup stays locked until you tick a single checkbox. The EULA contains this sentence:

> By accepting this EULA, you consent to the collection of such telemetry data.

- **There is no separate choice.** Accepting the licence *is* the telemetry "consent", and the software can't be used without accepting the licence.
- **It isn't published anywhere else.** `fileflows.com/eula`, `/terms`, `/legal` and every similar path return *Page Not Found*. The download and pricing pages don't link to any licence terms.
- **The docs tell Docker users to skip it.** Setting `FF_EULA_ACCEPTED=Yes` bypasses the screen, and it is *"intended for automated Docker deployments where the EULA has already been reviewed and accepted"* ([docs](https://fileflows.com/docs/variables/environmental-variables/environmental-overrides)). There is nowhere to review it first.
- **It is an agreement with nobody in particular.** It opens with *"a legal agreement between you and FileFlows"*. FileFlows is a product name, not a company. There is no company name, address or contact. You can only terminate it *"upon written notice to FileFlows"*, without an address to send that notice to.
- **It is governed by the laws of New Zealand,** with no mention of the protections EU consumers keep under their own law.
- **The agreement text is English only,** even when the setup screen is shown in German or French.

### 4. A privacy policy that doesn't cover the software

The only privacy policy is at [fileflows.com/privacy-policy](https://fileflows.com/privacy-policy). It is effective since 1 July 2023 and has the following gaps:

- It covers only *"users … who register their email and username on our website"*. It says nothing about the application or its telemetry.
- It names no controller, no contact details (only *"please contact us"*), no legal basis, no retention period, no data-subject rights and no right to complain to a supervisory authority.
- It relies on implied consent: *"By accessing and using the Site, you consent to the practices outlined in this Privacy Policy."*
- It says server logs are used to *"track users' movements, and gather demographic information"*.
- It ends with: *"Please note that this is a generic privacy policy and may need customization to align with your specific website and applicable laws."*
- It isn't linked from any page. The site footer contains only a Discord icon, a Reddit icon and a copyright line.

### 5. Who is actually behind it?

- The EULA, which is the only agreement you ever accept, names *"FileFlows"* as the other party and as the owner of the software. "FileFlows" is not a registered company, and not a registered trading name either.
- The website footer says *"Copyright © 2026 Reven Software"*. Until at least late May 2026 it said *"FileFlows"*.
- The actual company, **Reven Software Limited**, was only incorporated in New Zealand on 9 October 2025 ([NZ Companies Office, no. 9377517](https://app.companiesoffice.govt.nz/co/9377517)). Its name appears to customers only on the Stripe payment page, after you click "Subscribe".
- fileflows.com gives no legal name with legal form, no geographic address, no email, no phone and no registration number. Contact is a web form. There is no imprint, no terms of service and no EU representative (GDPR Art. 27).

### 6. The website tracks you without asking

- Every fileflows.com page loads Google Analytics (`G-QSCG4CDWTH`) straight away, including the privacy policy and the 404 page. There is no cookie banner and no consent mechanism of any kind.
- In a clean browser, the first page view already sets the `_ga` and `_ga_QSCG4CDWTH` cookies, which last about 400 days, and sends data to `google-analytics.com`.
- `/docs` and `/news` embed YouTube videos from `youtube.com` rather than `youtube-nocookie.com`, which sets YouTube tracking cookies on page load.
- The privacy policy mentions none of this: no cookies, no Google Analytics, no YouTube.

### 7. Buying a licence

- Licences are sold through Stripe payment links. The checkout shows no terms of sale, no refund policy and no information on the EU 14-day right of withdrawal, and it asks you to accept nothing.
- The seller's address is not shown before purchase.
- The EULA refers to a separate *"paid license agreement"*, which is not published anywhere.

### 8. "Never FOSS"

In August 2025 the developer wrote:

> The software was never FOSS — only some code was public as a showcase.
>
> — [source](https://reddit.com/r/selfhosted/comments/1ms1q9x/fileflows_update_25083_now_limits_nodes_in_free/n929xxy/)

In August 2023 the same developer had written: *"The code is completely viewable, so you can see the telemetry I'm grabbing."* ([source](https://reddit.com/r/selfhosted/comments/15jledo/fileflows_self_hosted_file_processing_videos/jv24l2o/)) The application's source was on GitHub until at least mid-2024: more than 3,400 commits, including every change quoted above.

He also added an **AGPL-3.0** licence to the FileFlows repository on 18 November 2021 ([`fb87999`](https://github.com/FreekingDean/FileFlows/commit/fb87999efe83d8e8bd0b768c84936ff3afd2990c)) and deleted it again on 27 December 2021 ([`73f030c`](https://github.com/martinkeat/FileFlows/commit/73f030cbac3d28379721f3c3c05a7128486a163c)). Copies made in between are still public under AGPL-3.0, for example [FreekingDean/FileFlows](https://github.com/FreekingDean/FileFlows). In that code, every user could switch telemetry off:

```csharp
if (settings?.DisableTelemetry == true)
    return; // they have turned it off, dont report anything
```

---

## Why I consider this unlawful in the EU

This is my own assessment, not legal advice, and no authority or court has ruled on it yet.

- **EU law applies, even though the company is in New Zealand.** The GDPR covers non-EU companies that offer goods or services to people in the EU, *"irrespective of whether a payment … is required"* ([Art. 3(2)](https://eur-lex.europa.eu/eli/reg/2016/679/oj#art_3)), so the free tier counts. FileFlows is clearly offered to people in the EU:
  - the app ships in German, French and other EU languages;
  - the checkout sells to EU buyers;
  - the company's own website says *"Our customers span every continent"*.
- **The data is personal data.** A permanent installation ID sent together with the IP address identifies an installation, and with it a person. See [Art. 4(1)](https://eur-lex.europa.eu/eli/reg/2016/679/oj#art_4), Recital 30, and the EU Court of Justice's [*Breyer* judgment (C‑582/14)](https://curia.europa.eu/juris/liste.jsf?num=C-582/14).
- **The consent is not freely given.**
  - Consent bundled into a licence agreement must be *"clearly distinguishable from the other matters"* ([Art. 7(2)](https://eur-lex.europa.eu/eli/reg/2016/679/oj#art_7)).
  - Consent made a condition of using a service that doesn't need the data is not freely given ([Art. 7(4)](https://eur-lex.europa.eu/eli/reg/2016/679/oj#art_7), Recital 43).
- **Consent cannot be withdrawn.** It must be as easy to withdraw as to give ([Art. 7(3)](https://eur-lex.europa.eu/eli/reg/2016/679/oj#art_7)). For free users there is no way to withdraw at all, except paying.
- **Users are not told what the law requires.** That covers who the controller is, how to contact them, the legal basis, the retention period and the user's rights ([Art. 12–13](https://eur-lex.europa.eu/eli/reg/2016/679/oj#art_13)).
- **Privacy is not the default** ([Art. 25](https://eur-lex.europa.eu/eli/reg/2016/679/oj#art_25)).
- **There is no EU representative.** One is required for a non-EU controller whose processing is not occasional ([Art. 27](https://eur-lex.europa.eu/eli/reg/2016/679/oj#art_27)). A daily telemetry report from every installation is not occasional.
- **Reading data from people's devices needs consent.** This applies to the app's hardware and usage data even if it were anonymous, and to the website's Google Analytics and YouTube cookies ([ePrivacy Directive Art. 5(3)](https://eur-lex.europa.eu/eli/dir/2002/58/oj); [EDPB Guidelines 2/2023](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-22023-technical-scope-art-53-eprivacy-directive_en); [*Planet49* (C‑673/17)](https://curia.europa.eu/juris/liste.jsf?num=C-673/17)).
- **Buyers must get the trader's identity, address and withdrawal information before paying** ([Consumer Rights Directive 2011/83/EU, Art. 6](https://eur-lex.europa.eu/eli/dir/2011/83/oj)).

## What I am doing about it

I am filing a complaint with an EU data protection authority. In my view, FileFlows should not be allowed to operate like this in the EU, and I expect the regulators to put a stop to it.

Until then, I am done with FileFlows. I will not maintain, build or promote anything for it.

---

## What this means if you used this image

- **The images are gone.** All `ghcr.io/lusoris/fileflows-real-image` tags have been deleted, and nothing will be rebuilt.
- **The images never changed FileFlows' own code.** They only replaced some vulnerable third-party libraries bundled with it. FileFlows itself, including its telemetry, was untouched.
- **The repository is read-only.** The documentation remains in [`docs/`](docs/), and the previous README is [in the git history](https://github.com/lusoris/fileflows-real-image/blob/6730359/README.md).

---

## License

The Dockerfile and build recipe in this repository remain licensed under the [European Union Public Licence (EUPL-1.2)](LICENSE). FileFlows itself is subject to its own licensing.

*Archived on 28 September 2026.*
