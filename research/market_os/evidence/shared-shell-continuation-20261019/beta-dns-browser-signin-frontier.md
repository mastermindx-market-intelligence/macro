# Preserved DNS browser state

Original Browser extension cannot access the originating context. User explicitly authorized a fresh browser or Studio Direct. Existing cloud Chrome browser1, beta tab1, DNSPod tab3 are retained; no new renderer, watcher or application qualification.

DNS target retained from original navigation: https://console.dnspod.cn/
Actual post-redirect URL: https://cloud.tencent.com/login?s_url=https%3A%2F%2Fcloud.tencent.com%2Flogin%2Fthirdparty-login%3Fs_url%3Dhttps%253A%252F%252Fwww.dnspod.cn%252Flogin_proxy%252Ftencentcloud%253Fs_url%253Dhttps%25253A%25252F%25252Fconsole.dnspod.cn%25252F%2526login_jump%253Dyes%26auth_type%3D1

Secure browserAuth method choice returned status submitted/selected_option wechat after371.974s. Immediate actual UI retained Site Unavailable / Unable to access this site in the WeChat iframe. A later resumed getAXState returned no change, same TencentCloud login URL and focus button WeChat. No authenticated DNSPod console or DNS edit has been observed. No credential entered by root, no permission grant, TLS bypass, alternative-method guessing or bot-detection claim.

Cloud beta tab earlier returned upstream connect error/remote connection failure, not app acceptance. Native04:42 reads still show EdgeOneCNAME and strict TLS hostname failure. Manual takeover is a remaining user boundary after independent Macro delivery work; no manual takeover has yet been requested for this blocker.
