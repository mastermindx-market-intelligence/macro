/* Browser-only offline fixture test. Requires puppeteer + local Chromium;
   no market source, Supabase, SMTP, analytics, or production URL is accessed. */
"use strict";
const assert = require("node:assert/strict");
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const puppeteer = require("puppeteer");

const dir = process.env.CATALYST_PREVIEW_DIR;
if (!dir) throw new Error("CATALYST_PREVIEW_DIR is required");
const assetRoot = path.resolve(dir);
const browserPath = process.env.CATALYST_BROWSER_EXECUTABLE;
if (!browserPath) throw new Error("CATALYST_BROWSER_EXECUTABLE is required");

const calls = [];
const fixtureSource = {
  source_id: "sec:fixture-earnings", display_rights: "ALLOWED",
  rights_receipt_id: "fixture-owner-receipt-only", title: "SYNTHETIC TEST FIXTURE — SEC-shaped source",
  url: "https://www.sec.gov/Archives/edgar/data/78003/fictional-fixture",
  published_at_utc: "2026-10-09T01:30:00Z"
};
function packet(tickers) {
  const rows = tickers.map(ticker => {
    if (ticker === "NVDA") return {
      ticker, status:"SUPPORTED", relationship:"DIRECT",
      headline:"<img src=x onerror=alert(1)> Synthetic fixture, not investment research",
      correction_state:"CORRECTED", as_of_utc:"2026-10-09T02:00:00Z",
      what_changed:[{text:"Synthetic correction notice linked to a mock filing.",evidence_ids:["sec:fixture-earnings"]}],
      scenarios:[{case:"BASE",trigger:"Test only: await the next official amendment."}],
      invalidators:[{text:"Test only: the filing could be retracted."}],
      sources:[fixtureSource,
        {...fixtureSource,source_id:"malicious-src",url:"javascript:alert(1)"},
        {...fixtureSource,source_id:"private-src",url:"https://www.sec.gov/Archives/filing?ref=ok%26token%3Dsecret"},
        {...fixtureSource,source_id:"identity-src",url:"https://www.sec.gov/Archives/filing#visitor%40example.org"}],
      dossier_path:"/stocks/NVDA.html"
    };
    if (ticker === "AMD") return {ticker,status:"RIGHTS_BLOCKED",what_changed:[],scenarios:[],invalidators:[],sources:[]};
    return {ticker,status:"NOT_COVERED",what_changed:[],scenarios:[],invalidators:[],sources:[]};
  });
  return {
    schema:"catalyst.scan/v1", schema_version:1, requested_tickers:tickers,results:rows,
    event_id:"fixture-earnings-20261008",generation:0,as_of_utc:"2026-10-09T02:00:00Z",
    publication_state:"PARTIAL",coverage_note:"SYNTHETIC TEST FIXTURE; no real market claims.",
    scan_receipt:"synthetic_HMAC_fixture_not_real."+"x".repeat(44)
  };
}
function server() {
  return http.createServer((req,res)=>{
    const file = req.url.split("?")[0];
    if (req.method === "GET") {
      const map = {
        "/catalyst-scan.html":["catalyst-scan.html","text/html;charset=utf-8"],
        "/catalyst_scan.js":["catalyst_scan.js","application/javascript;charset=utf-8"],
        "/catalyst_scan.css":["catalyst_scan.css","text/css;charset=utf-8"],
        "/theme.css":["theme.css","text/css;charset=utf-8"]
      };
      const entry = map[file];
      if (!entry) {res.writeHead(404);res.end("Not found");return;}
      res.writeHead(200,{"Content-Type":entry[1],"Cache-Control":"no-store"});
      fs.createReadStream(path.join(assetRoot,entry[0])).pipe(res);
      return;
    }
    if (req.method !== "POST") {res.writeHead(405);res.end();return;}
    let data="";
    req.on("data",d=>data+=d);
    req.on("end",()=>{
      let body={};
      try{body=JSON.parse(data);}catch{res.writeHead(400);res.end("{}");return;}
      calls.push({url:req.url,body,contentType:req.headers["content-type"]});
      const respond=(status,obj)=>{res.writeHead(status,{"Content-Type":"application/json","Cache-Control":"private, no-store"});res.end(JSON.stringify(obj));};
      if (req.url === "/api/catalyst/scan") {respond(200,packet(body.tickers));return;}
      if (req.url === "/api/catalyst/optin/request") {
        respond(202,{status:"VERIFICATION_REQUIRED",public_ref:"opaque_fixture_ref_123456789"});return;
      }
      if (req.url === "/api/catalyst/optin/verify") {respond(200,{status:"verified"});return;}
      respond(404,{detail:"Not found"});
    });
  });
}

(async()=>{
  const httpServer=server();
  await new Promise((ok,err)=>{httpServer.once("error",err);httpServer.listen(0,"127.0.0.1",ok);});
  const port=httpServer.address().port;
  let browser;
  try {
    browser=await puppeteer.launch({executablePath:browserPath,headless:true,
       args:["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"]});
    const page=await browser.newPage();
    await page.setViewport({width:1280,height:850,deviceScaleFactor:1});
    const url="http://127.0.0.1:"+port+"/catalyst-scan.html?utm_source=fixture&email=do-not-share%40example.invalid";
    await page.goto(url,{waitUntil:"networkidle0"});
    const initial=await page.evaluate(()=>({
      boot:document.getElementById("cs-js-needed").hidden,
      disabled:document.getElementById("cs-scan-controls").disabled,
      optin:document.getElementById("cs-optin").hidden,
      preview:document.body.textContent.includes("OFFLINE UI PREVIEW")
    }));
    assert.equal(initial.boot,true); assert.equal(initial.disabled,false);
    assert.equal(initial.optin,true); assert.equal(initial.preview,true);
    // Respect house light appearance without writing any identity or consent.
    await page.evaluate(()=>localStorage.setItem("theme","light"));
    await page.reload({waitUntil:"networkidle0"});
    assert.equal(await page.$eval("html",n=>n.dataset.theme),"light");
    await page.evaluate(()=>localStorage.removeItem("theme"));
    await page.reload({waitUntil:"networkidle0"});
    await page.$eval("#cs-tickers",n=>n.value="NVDA,NVDA");
    await page.click("#cs-scan-submit");
    assert.match(await page.$eval("#cs-scan-error",n=>n.textContent),/duplicate/i);
    assert.equal(calls.length,0);

    await page.$eval("#cs-tickers",n=>n.value="NVDA,AMD");
    await page.click("#cs-scan-submit");
    await page.waitForSelector("#cs-results:not([hidden])");
    assert.equal(await page.$$eval(".cs-result-card",nodes=>nodes.length),2);
    assert.equal(await page.$$eval(".cs-result-card[data-state='RIGHTS_BLOCKED']",n=>n.length),0);
    assert.equal(await page.$$eval(".cs-pill[data-state='RIGHTS_BLOCKED']",n=>n.length),1);
    assert.equal(await page.$$eval(".cs-source a",n=>n.length),1);
    assert.equal(await page.$$eval(".cs-result-card img",n=>n.length),0,"untrusted headline escaped");
    assert.equal(await page.$eval("#cs-optin",n=>n.hidden),false,"scan first then optin");
    assert.match(await page.$eval("#cs-summary-status",n=>n.textContent),/1 OF 2 SUPPORTED/);
    assert.equal(calls.filter(x=>x.url==="/api/catalyst/scan").length,1);
    assert.equal(calls.filter(x=>x.url.includes("optin")).length,0);
    await page.screenshot({path:path.join(assetRoot,"desktop-1280.png"),fullPage:true});

    await page.evaluate(()=>{
      Object.defineProperty(navigator,"clipboard",{configurable:true,value:{
        writeText:async val=>{window.__copied=val;}
      }});
    });
    await page.click("#cs-copy-link");
    const share=await page.evaluate(()=>window.__copied);
    assert(share.includes("tickers=NVDA%2CAMD"));
    assert(!share.includes("email=") && !share.includes("utm_"));
    assert(!share.includes("synthetic_HMAC_fixture"));

    await page.$eval("#cs-email",n=>n.value="fixture@example.invalid");
    await page.$eval("#cs-consent",n=>n.checked=true);
    // The client must pass actual elapsed time, not forge its bot-delay signal.
    await new Promise(ok=>setTimeout(ok,3150));
    await page.click("#cs-optin-submit");
    await page.waitForSelector("#cs-verify-form:not([hidden])");
    assert.equal(calls.filter(x=>x.url==="/api/catalyst/optin/request").length,1);
    const c=calls.find(x=>x.url==="/api/catalyst/optin/request");
    assert.equal(c.body.consent_checked,true);
    assert.equal(c.body.scope,"catalyst_event_updates/v1");
    assert(c.body.form_elapsed_ms>=3000);
    assert.equal(c.body.first_touch.utm_source,"fixture");
    assert.equal(c.contentType,"application/json");
    assert(!c.url.includes("fixture@"));
    await page.$eval("#cs-otp",n=>n.value="123456");
    await page.click("#cs-verify-submit");
    await page.waitForFunction(()=>document.querySelector("#cs-optin-status")?.dataset.kind==="success");
    assert.equal(calls.filter(x=>x.url==="/api/catalyst/optin/verify").length,1);

    await page.setViewport({width:320,height:740,deviceScaleFactor:1});
    await page.reload({waitUntil:"networkidle0"});
    const width=await page.evaluate(()=>({view:window.innerWidth,scroll:document.documentElement.scrollWidth}));
    assert(width.scroll <= width.view+1,JSON.stringify(width));
    await page.$eval("#cs-tickers",n=>n.value="NVDA AMD MSFT AAPL AMZN META TSLA GOOGL INTC TSM");
    await page.click("#cs-scan-submit");
    await page.waitForSelector("#cs-results:not([hidden])");
    assert.equal(await page.$$eval(".cs-result-card",nodes=>nodes.length),10);
    const mobile=await page.evaluate(()=>({view:window.innerWidth,scroll:document.documentElement.scrollWidth}));
    assert(mobile.scroll<=mobile.view+1,JSON.stringify(mobile));
    await page.screenshot({path:path.join(assetRoot,"mobile-320.png"),fullPage:true});

    const nojs=await browser.newPage();
    await nojs.setJavaScriptEnabled(false);
    await nojs.setViewport({width:320,height:740});
    await nojs.goto(url,{waitUntil:"domcontentloaded"});
    assert.equal(await nojs.$eval("#cs-js-needed",n=>n.hidden),false);
    assert.equal(await nojs.$eval("#cs-scan-controls",n=>n.disabled),true);
    assert.equal(await nojs.$eval("#cs-optin",n=>n.hidden),true);
    console.log("CATALYST_BROWSER_PASS desktop=1280 mobile=320 noJS=locked scan_first consent_OTP_and_privacy=verified");
    console.log("FIXTURE_ONLY_API_REQUESTS",calls.length);
  } finally {
    if (browser) await browser.close();
    await new Promise(ok=>httpServer.close(ok));
  }
})().catch(e=>{console.error("CATALYST_BROWSER_FAIL",e.stack||e);process.exitCode=1});
