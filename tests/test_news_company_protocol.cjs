"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),company=require("../templates/news_company.js");
test("company identifiers and URLs stay within the incumbent read boundary",()=>{
 assert.equal(company.ticker(" $nvda "),"NVDA");assert.equal(company.ticker("BRK.B"),"BRK.B");
 for(const symbol of ["../feed","NVDA/stream","<script>","A?token=secret"] )assert.equal(company.ticker(symbol),"");
 assert.equal(company.safeURL("javascript:alert(1)"),"");assert.equal(company.safeURL("https://secret@example.com"),"");
});
test("snapshot identity and paging cursor are validated before display",()=>{
 const row={story_id:"a",title:"Report",sequence:4},p={schema:"ticker_news.snapshot.v1",ticker:"NVDA",rows:[row],has_more:true,next_cursor:4};
 assert.equal(company.validSnapshot(p,"NVDA"),true);assert.equal(company.validSnapshot(p,"MSFT"),false);
 assert.equal(company.validSnapshot({...p,next_cursor:null},"NVDA"),false);
 assert.equal(company.validSnapshot({...p,rows:[row,row]},"NVDA"),false);
});
test("SSE parser accepts partial UTF text frames, CRLF and comments without inventing rows",()=>{
 const events=[],parse=company.streamParser((event,p)=>events.push({event,p}));
 parse(": heartbeat\r\n\r\nevent: up");parse("sert\r\ndata: {\"sequence\":7,\"title\":\"更新\"}\r\n");
 assert.equal(events.length,0);parse("\r\nevent: restricted\ndata: {}\n\n");
 assert.deepEqual(events,[{event:"upsert",p:{sequence:7,title:"更新"}},{event:"restricted",p:{}}]);
});
test("malformed or unbounded stream frames fail closed",()=>{
 assert.throws(()=>company.streamParser(()=>{})("data: invalid\n\n"));
 assert.throws(()=>company.streamParser(()=>{})("x".repeat(262145)),/large/);
});
