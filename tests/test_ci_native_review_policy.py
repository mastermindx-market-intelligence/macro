"""Offline, network-free focused fixtures for ci_native_review_policy.py.

The canonical policy sources are embedded compressed below, byte-exact for the
two pinned revisions (verified by sha256 + Git blob SHA1 + size before use):

- baseline  899ac3a9f2c70478202f8578c52b7b8890dbc5aa
    AUTOMATIC FAST 0/0, STANDARD 1/1, CRITICAL 2/1 (accepted source)
- prospective fe0e7fc84dca8afd30d4dd0ae932da12403e96f1
    AUTOMATIC FAST 0/0, STANDARD 0/0, CRITICAL 1/0 (fixtures only, NOT a
    runtime pin - runtime always uses the actual current protected branch)

Every request is served by an in-process request-sensitive ``get`` shim; the
canonical modules execute in the production isolated child (``-I -B``, no
network, no token). These tests make no live GitHub, CI, queue or service
effect.
"""
import base64
import binascii
import hashlib
import importlib.util
import json
import os
import sys
import unittest
import zlib
from datetime import datetime, timezone

_BASELINE_REF = "899ac3a9f2c70478202f8578c52b7b8890dbc5aa"
_PROSPECTIVE_REF = "fe0e7fc84dca8afd30d4dd0ae932da12403e96f1"
_PRODUCTION_REPO = "mastermindx-market-intelligence/macro"
_CANONICAL_REPO = "mastermindx-market-intelligence/Mastermind"
_HEAD = "a" * 40
_BASE = "b" * 40
_NOW = 1762100000.0

# (ref, filename) -> (blob_sha1, sha256, size, zlib+base85 bytes)
_FIXTURE_BLOBS = {}
_FIXTURE_BLOBS = {('899ac3a9f2c70478202f8578c52b7b8890dbc5aa', 'github_review_risk_policy.py'): ('f6627d28b3850e839ea2c4dde3d96c1116a4a52e', '33c333c391b9ca5d2d21c55d78a1660ee68e208137fbee8c7a7edf0547c826c4', 16557, 'c-pl)Yj@kYa^LkUP^G6U?MjrL?%uZE`kt$m=|o-IawR#*HaF#=NJwH#kqk&W)~5OIof!Zm_>doInzL(xATSsV=8a*u+a3FNK^lua6G3{*vVaS=js<gB8t1~}!#gg5b-;c0D#%{vD|S6+ez0C!oz8L_qzwLZna?vWc0m-RS>UlG4g+t`f+)!|mc=aFa`q#?$CuIOM<#g4-IOyo@}Yef@Xww2bHqhDU{|vxK-+P#;RE%Kive?!M8tP)IAD|MfPId|Eg*?F`nw=agE(Sto^4|hWP7V~?s{3uc6pky6=z-?hTO{l{k4d9uqF-V5#Z@!ua^q}Ps1&DiyaDR4_L%u=N+1bTjr@Jf+T~*25PmT7e|>u_&y8W6%SLwX#?O`%ER^0%`%>5F3zz!-ELO`bDVXa<$^m73wB8?GC(Sd<*>BVQGLFfxnAg|DNl8m;1U3j@|~V)L%Y*iOkUfUV|L2AJ2#al;ai&^+vY1rQqjS~bqHL#0|c$R<8H@UydM921k(h!ym*%cA@7Oqf4@H({+l~ofB5qA(bs?M_B+npzMeHljfel`4*!I)jy3%7<#=#>bo6!9+Dkw#$M2l$@$&ToAiezMFS6s(Ue2cz=s7-ej*jU6j&nX<Ea~mV^vb5;KUccXrx(=y^N|FywBf~>ePJ)Bvnzb@%TcHEf{j_abHk8@L4<6O!>JHc(7CeJJ^^a5OhDIg1#f*9L|~+uK6F1T{<AvHWIkO^C*up}dTyUj-_hc|4ugMPMdeX<AfNr%OGjxOI_Yf?hH10E+QEr?tDXFwdwCYz@oG2mRkcf<aHUTjcXg^3j-oqG%yr@tPsP$s61ou|RavNgOcUK8%J@b|em(%AG9=A%KZqSa5Fn_|&Pxhxq{yWspC@5lVz0ZEA}RX;6WnGwzj_Esm~Vope6~Qqa-SQ|vCr>~$6SD7ENK%IO_b|&gnu0`a9VmbDsAuZINJJaG&0^ug=!waI@pZzNaT@213tTO03x;ayRbIML{GRrDBzMD?jBV^Nskp!%N(!^iZd$sX*Fu=1!c8@lW2Rl4k9=53O<P=eA73C%6>PVEJ30`xBbbZlxMv!a_0DzeYIRzJ70sET#RqdY@;LD<L)i6JH;O3d-E}h@7JKOtYlyENR}s-x8Bs5snnbf8kjV3J#(Hs4J0ZpS$`ohaTJFcuaiBPu8+XjRu-3sGnt*)v$t3Fe4%?5_T&aA@`tfIb%Lez?%bqy!mV-$T#*Gk6Zr#DEv3gW3grya8*~89*>rp{dv#+w3wyBu4eLxUW((W77{4`erSTJc1}bv)ANFMFTwjb~<m_rWy}GGxi-v-_p1!f?e>iVv^WV=eW(`>OJ0Qps#?T0R?#yTKc=gJeydF>ImjHZxc4l9l-CWjZ&h0l-`>ivdE`E2eXBX2+WARth<?EZ@95oPt&S7WeATS-C#}o7pUc5Xy{#P&_5x6cHajzSWv~05kkD84m^iN#$BEmiRPtl(IBXEBdG#7f}HF`nd^pFVxr(n;t05Gse5d#ARRtY^Npdx$ASIYb_DcV-sK>~~3^32(QBXjt$W0*}6cyLGxiUHJd;5q25)W#tP)(5m`83c%am-$Y>eqG^hN0(r^?fK>O>I_eB4sGYnOXE<^W)pA&u9RedHI>7{eszgjpiMuZU~~uaS2=WWK)MG+=Fg%d)?@YAskY!*YFH0=#24`EBS1H-KBf4Wppqc7U42SRGeIv%WmAh(L!l2ua0eP`!|9cNAjnyK%cG)^%C+}N7GsM?)TU*X4Hv*MPN7z5B4~Kt)|Cc-f?}s7mC~;n0eq#@zn-O<v`o<;tX2XL6dFQhIccdiL{y~fF#cQ;#3{6yI_br7e04USpEZ4}7i<m;B<?^Aflo7tNp>T{Z=mo&8W%Vk<+oupvU9yHxO_uUZ+Gb8TMF7tz?RU-lL))3kdt*aros`&%*_}o#*AsyU;rtCzx<FYP?IV9l)E8@MFQkBb3qZX0HO}TKjq-Y_~3d1iI}(L-fh|{yGW9X7la+!R>}hhOTtIwx0`Mov4xa6X-EqS9yFwN8-$`scoHXA*?lHC!@C71)B2c}Jf`}FVeH+i7p%K?MPy+Q&5Dwpe7$!K`{s&GT&yOa^bBb3Vqdk=d{<|LheSRFitbzzUTP6L7EVXyA(i_CQh7lbxTfSFO(jdFfu5(^QpO>)S_8k5<fXwTlA1uaO3@K<vXvSGP|QMJusvUG<CvCEwwQqCtFX{fTICdqq%IeQ27Em|Knn_8938q;6k4ep3k~BtQZJbTs?{{Pou$GmgsQ4Z0tl4R$qYbn>SuNk$s8ouS@ErV7sRAR&{cG_xsWO@PE!X3J@9yWvZaC9B_Y2DZ)FV=6bz7Bk$dFqcw0BxXne*OCB5nt{2x|Bx8s1_0ijviR|^$5_PS((!1Wg?A*W@-N~AKhJ|_B?%LbfvLXAzZ#xR$HQB#*G2a&WYw5Z{b*Pc4g2&Qy86z8)!aOE`}!W0uHwh*!Cy>Y{wQ?q{}3DWH@!AVd$D~;SF-Nu>Jdm-vb?*FPn+)QxLWkJSVOwnNY4Eo9A;O$zNj40Nn^Iw80>j7B@lu}TO(VSD(#osRV6gm-lbz8nE+!=VI+w#rp*#(WqUtIQYMsC9@+C9lTr%RFZeg(C2VBiHf9ulX-&9*1tK?!<teP4?03HVzXb@`z9Yh4NQc$}wBF&Wt5Dvmgyg+Jeb)P(qsa!nF1!AXV0VqapH<YDLlIagei$Y7?)Nw;n}O!BZ#*a6lMpoIKAorPstAD*#KFme(4puixc9e5?B#l?sm(>t(Su)|m|&y5%eD@+I|6~d*dk}{Wp+dy3A=nUWqTg7pxR(cJKBGZ9yi)$)tE0c(5n#s`xNL(e}3XD{CkWzkfJ+g6IgxA<SN>E?#Es+j57;qpv1J`Sa!5!Q2Oaxx~Yh~X`Kven<_Nq3aO*o7Nq&8@|vsy|pi!;#j12p?^)ZqJhd`Nr5)l%liEQ&J<3i2H<!7<Dp4CPs}Rqk(iX0f*rYsHuamCnD!lz~>H`JnV%)M9E$Nex`ZQ6n`ys)AsW=J}k9dS+b2e3E&k&Mi6e|G><cKt3^)3Uy*?c$e=Sh^~3UBlM?@xYOWZJrFe+7@#PQl*j1k9I!DMm^vl?uS*QQ{Tte6F0#FnmNi?0SLdMj<pAURC<DBQiP}CJ{*_o;5<{ukt2isu%9zHcwDbw3phG;gZ5;Y3@p>drQRK)U5GsZthJ@js^sEL6ra2c8Wri)vvInN_wNS^xX(FDEl2G1TlYVKc9Kskim&7=L=yIQ^;e7;*9C|=e5iV{3EZAysz@JZK!d!}314_5wT+=EUrdS@eEXW;YkF7N@&(6)fZTt9gE019pL_{2eLtF7Nn6*F%*ai`53}F9$%8s75I?iTtcI)z5EE>e1jC+F`mEljPg`QSicDM|JEiOE~UBNX_`!iUw6~~IzDG()5LR3Q@wGaF&D|7iz!?OawK$d)0RJgdN!ZGDMIzgj^;*2^Dok{r$Z>10f93*SOti(m{6T9mtfX&`99yxAMj(~?>j$igm08eEDwLW2`@K@_&kCkSw$kNYX0(xEW^l<s^-~Zl4{AnL}TNLek5Lov-z=HkrOYBmQr>E@r<-gFTJw4+YDCSY>uK5EP;>s!Cp#DYhU%KSQ(jTk)mDV+0%l#x_kkMA2fe5H@(6(^|#x;D5V8p$>J}yXn@Z?2&;2^TzjJ%qZ<K5gEy70#F(5kqE1&&qET)Sko$OYd8FzIy*=Sv13%I)eJM7TpY9hentzMEx23eJE)^c!qRgX>xen@7lr5)?Fy3$iB@V%`0MYkqAJGB|>WZ=|83#KQsAb;$WE5Uv`^2j%_%s0wy*$la*jrW9^rQ#&E|7C6ux99S22>{CQ$MsT>+uL?y{E=555PupKPtJsmWnYR&mw~VL2@)Yk&_mNK4FrTP^P`fpD+h_l9YUp3%&C~EIrGdP0n%YWX)75;)0#wI6-vF5NAJPAEln#Yj?SLBMVP?CGnhu%_&|qR;9(BdNZpbDLu6a<}?PeO7McP~O)q|GkDTGn`VF6{C!PS&P2Bbl!)6`vQRb`gAn2NJPz;95X21>?qCREay&BYsoD+l!Gq;f-Mu&z&{>J+K*z4FMavrIiunS}q!Q>-j>_&A>kq2&-N6sXzE$4*4UW(9VS^2AeU--dAs;kkCN&Gykkb=&tn?cZ~RN-LWuS;3})keQ4YlA?yLx+qV?C}r_3DDE806FiJSY3b5@*IQe~xzKs7+jScm5!qdg?-(2`K^3R^L{P=}=h(^0_Eq|X!k=2=#ocTK9uB9hC`H18r+JtijDrV_bi;uCSfm9&`YBL8ocDOasD`Zw^M?`7GXaijnVcx@g;c`FXRAHKn*eByZ<e#m@p3v*z+|#*Wb3PVASdi71vEcz1K94?MV_zkI?FI4;twbGZ1|S16fD4J1E=8!SfH>AB23s>?03!+N;bLridtQFsq5k)S^UcNPO(wWfO3J@xzP`}rEo}Dh$tRH59I^*!^)jA?wl$C6@qv(t$^YEv?LnScYLgO@M52h*tNWXVwi5D)IAWhudmx>)!!zJSCri2J4*D?+N(Glm3J6L=^*lIarLK&Y;H8xsX{<9237-2ptiP+)%|<QX6NTDk3yIVqMW#R$Bl{12yX_}t)aRbq3W>|bljJM-)oth6V^K#up_ml+5nv>he5{!cHBNl=geWy%Y%b3g<f6it4t4<xwNucGNqb5V*~H;z&~`1WK^4E7}|!if~T^&a9|{|bn4}_p3Er+8TpmdM#iNarc)TF)kH`+08u{0KV{b=$;4BW7>!8}Bo<GLmbq8bC8y+~_IwB^Elg+M@_pJ<@A~Q_3Y`_C4u~v@cSy#fSKK<(5{+bj;gC#QTm%R74g>R~a4aYRLa|J>c<Sp(J;{h!-wGs46u~<(*Zbk|2LfIuJgL4gRrg=AFit&C6`g(&`&<_5c1t1^RTcX7Ocu^jI#fPm4W@dOT>Au!;be90#4Nj_G)iMcv;M08;1U==N+3p(2ArdHaIff0?JBYLwcZ1uvFub9GGawFsVNAf(4)d&7@XJ$?*br}z&^Z|GnAXY%C*!zmmrmc!3?%l`b&_PD!59<i0=ClR@(jqbf*3EWimx%eN)bn=Xw(2Ke1+Yjmf$|55&U%4y;=*O=uomuWO~B=x$w>2lT(+sWl2q9svFSNb5#fgGp=2v)@E#jj|#~k(o0wDK$9~PVYzENb3vf%6&8yp1cJAt3m-<>-`DnjK1kXHqVk|RD#y+`|{yqYPRnU1=8{l7$f1Ho<r@d(!TGixCIINLS9va!ve+w>u(UFs-Hv^JeA6w6FDj6cteQyHs~i%ss`Z6(w$$8A|N%atRAWs`7j&H_*_{4h-y+67vYU7fHNx3@$!!rhDeSaE&SAiAQ5HQ*l@Sd(fR>>M&+3SB%gZ$eew{LZi~EPrCVI(nJTYv1p6hAkS+jW*Pi+sq0?~|H`mv*In`7)>)MOjJ$(a8bqhO?(Hu+1&CdLOXguqpSgfRV!x8y}i5Pl9*Dh6G$&{ePs#+{xd!sAnJpoY{mORvI>nkY9p?ShZf;<Wsgsv<}?suH&l|5go+K&STQ+Qjx)8<c=)z^DAdEi$%u+(K(_EJGgxmJ_J#iUUcW?DY4-B0C12Cl5YDnzx9H`B!p>hPQM`ZozrD^|hZz>AA&_s{WKc4FhDNvoy(ZdqBUwM+(v+i#|4_SM9$4c3KYvN#lf-JMqY5-~5mqu*@?FDlk3Pp}vZTzpmOb5K)uyIm@Nkhxd<xC2E?v&8_#PB2Me3aamdG*^KhNHr)86?s_l_V^}}fba_0Rl&riD{g)4#9KOuSyHs^SoG_b5(@FHms2q{fw4<%VbmJR^`tr|cgQ}<WQFIViipA772boTxA>^>t(p~OrV3?kn9W`(iJ<XEO7oA}Oz=4{9dBCqnjn2Q%iR>3CQ3Ei)5@qnvAT@(zsZqk>dEhg4|X+VreebDa2p$vq9Q{c^INZnO9u{TM1aR8+c*XWMC(akP$Azc=3eCj#EBSH-sG(Ithm)tIV~-6N{}eQvd$xl`GMzQ8(1`(N2pXk<>+?+qbv9kkbWcFNcG8JzsLwkDY(RXYmk=OawwD-9uFwJL^t6w83MG)&G}l2YE>2mZ{YNYuflY`^1;-<I>1T>Yfz8nu{ic-KF7~2CbP@y3wvohXVdd@2h<CGO7X_NQZAj2C_(JsQ%3la+i<N5nvrP#gWhQYQ(dTStKp7uS=M$_)_=xcHB8v=a(=T|I<vVmzFEGW;U_Q7Z?hZpvHs8{04f4`>Q)<Wq&mdI_M=Z0pgr0t$y4A_Ay2L5^}CQq!$fwNT`lbYyaA4w!Vv(OBwxJ4FDI^E*$?H4%LT~*l&Rg*=OlZZMr2JlHs<{f2n~8709fWl){g-^d>jqnR0>z1T&B8zVyzp{xHPeoNiQaEQmex_*s}+yRZDe~!3e`%En+kBF|BnnxClFH?5mcN$9=VA)(>u^ZK>jBx4IE^Ph0&w_S?8}aq}BK5l<4lxqUf%GrlO<Q4^>|;2t5=Gcdxi39yl$g4yUI++a*S#+?yf3zQgbQH?8aqCL=~_GvMoRU@)FhQ2fYMtV(V*EYCC6WcypNQf8H%jvSKYgupTb1#ZX2gZl@6c^HMgAO+#fZIVZd5X1*tY^fieXICbjjkFn<RrC5p}hRWtO#D|6SL1-3Q#e3kD;ad_y9~Y_c6rOU#lt3q{MoWU@bnzrz+b(RAOHl-3q>Q;fQPb^QY4cTuA)fZ!x=>gEuq>B{-ei3uiKQ7MHW%@ihMzGupP;'), ('899ac3a9f2c70478202f8578c52b7b8890dbc5aa', 'github_review_risk_source.py'): ('0295ffb725c3ef29f94fbc6a644d044f09f93847', 'ff82c6d68706560935d5968979167eadb625a3701218f4f900ac76f32e6973fa', 8177, 'c-qZbZFAeW5&q6!fvR7q9?dv6(|&NPOch&BbZ1K%QBE$s$zUi7vT)(s0H7UT+yCC(1xb*SoY?72d!F$K!pmY`pWTH9gTYEw+K3H%BhA}t%@#|R?Be`Zutem#(rjBOW_E%psXv_<DHQBg;!cWtwvDx6X`GAD^H#7WiPKalc6}4A*jnZrI43n*sKOLUkup;dA(<ytwida8kv4E7HnPZ1bW)Tp8=eyJMyP=0g~4<8V!bPhPwa<iJ_}e}nH_MIq_NC&fGivF*#yAKTBI-mYcb1#!33Cvi)5UJz##CF6`Lv*I3F9KfqEl$l1kVZG?M*LtOHgGl}W9EIh;>LtOb(3SJDU-dSjMUN}(LOs8k}@4tQp83G&X?h1s#S0PP7DgDT=J9AZh4m8md-Z6&Z##<wyj=|gWY7<gM%WQ_A|Whx~&XEG}bW#BkyfwpPS?%Bj92I;j18R|{#l-*$-N}1m_i;W5D<4KVlRiwNm+ucgDtJd5~&e6=gEK->~G^c%!!QYbB&&f9~<HYEoGkpo-M8IQrZV8me$fC|rwRQ#O7DRlSmz9|)RVcec!ssp+fj9KL>+w(ga(Xq1*ob}q=f8N1@tX;crvI40_m`)q-uUWj{(f@7qt$qI6VWyh@mFwNVf=p*<w3mJh|M5i1F*i_N;_5}EAE<M9%pt4K3K2YAb_Fw@1e(EPiN!h2OiyAUQU0aTl_&-=C`;r{H1I@g&o|=Eq#L5mNbw_L7(NOUMRM1@cjTTSd3TaZ$Zq6Pu@*0CbRPiUo0o>WmXU+w1`!*djU!UzfQypD^>ETDs_Ld`h3#)ZjT%E=R8hdY>GtFE*jhk1zJhS!Eo<!Zu+99MJ=)}avD5jsr`)WK}K2(&1XZOiM|6dJ&#<J+#sT$xyj?ZSVG{Y!e3Sps+l0C7@k?40iOUebRL&_2T%af1)D5l1&AaN6B52)=)!akQUHcPkV0gq1sG5@K^kI!5zUR*LXgQ^8qR$!(ro|%u@PrX8#QDnuh^`}g}omCbOkuz55x8dZXUMFe`FC{oM6OmSg8PC5{mPU0Pqr^TNbOeG%8jP46I}T95N<8C!$1s6L5v@F5o7_v!G@AkXwvoVedrgfdB)H6T~Fw^Y3lk`_}JAfak!T)w9*{VrivOqAavDg?b=aX|Al&l;?=Y>J0R0XcB>p>s{=&tpWS`GqmRzMcR670pLA916%|cA~Ps}#Lo9R;5Z_qcDz9FN`gK&wE-;dOg&8rh)`AycmW2y;|#KpskHn4^*c#*h*d?Ud5<9b7nueONEV`vu}OBk^>ZsTY(OS^Az^dT5;VI2-1QsOcCj#q#E1FJx_Og+>J-+^rp)F~xT%8Nvj!+Pl$TOg+~<(IdclBud8sV)+gw)1#h-$GrwI-`hC-(AX!sX~;UhPox;Ugh;rIOhX}1NKG(|HMinm{h7%^ii$gw{=vj@n`$350Of`Pj@mEb(UkMdz$0jXmBi%5)RrD5VxNt^hjvlO6MurzxRh-f8ra<M;*h_qYlh=_}DS<9)4C4~BMv>Ys!JeuDu0h<w`SJTx8elz=VHh(`G3=f$LG5lH%$pf*lbL$k3y$#Ri1CuatGkZ6_nqD|2ke=hg32qVK$(PLLE53w$G<iRMeKm39EwMd3I#lx>E;SpTe*fFa_=1?2&UiGwo&Yn8c{E+kmmg|ouvA7M0B3<D*#k68f-S62>TLjJFmx<HVVMCi+zJ3BQ+s4UBwfO3tcrVEbAflFq;&po?6e)ff+C5Zp3=X&<|)!*(M1N04h?D*+LI4%ed%=FUwXybD(>mprtN%wv*Pnh9-Yq@jl~UMLrdkbYV;54RKG8G>j5Ji_7G-NLa;Z<Z`AQC_!{)6Gy(#&@ASwY1}<leP6L-M;7k8pUH{iG%Wdr?HlxcJlDgYF9R3eQY?Ax`MMPT)9c>IibX<N0480xm>+#j)e0e<qcV*P<0EN2xff_Bh4tfCp=&1b!&;ff_I(!N4an~NCHibdE6SB$kA^=5N9D&r%CAN6!Ug6@<uGI*^_Isu0vO>oo$3!=a#eBJ%Ty$a2V%|4H-0uqCI@;Z<-M%qD(q+_C9j54>rA8yyj-DN;q-JTq?%cP%%eRLm>a%pTz;rtYn*-}_`Smo4rn5IS=OS%+Ke(mgr{73D`?hOTSbZJYAw?j}i@ffT`auRg={+@SBH!qHX?Fg8*FHq$IH-K&I9NiNn!p#j@(w^lh5c1lzR*!yN=K@tJ>R2?aP>eJPuKDJ{GxHhzB!MeW1V>FE~72qQ68{#9;beN5<88vBMr>cDtfO|vmbppYRl=5Z6Aa;xVN;p>58be(*fJ!vj?O19m;hug*zB^T5|hPcP8WffzbnBeoI{iGE1Qc{YVZx%RA9Fc|<zE?HOtx_dvt~VeGj?+Ytw>%9Tip+g$z%d+3!9GHXehp~`ht;)@!dwoisiY%37-ulQbZIgVCn+ns$6=sc)ql{RGgq{tzi8YVD3YSdoQd8NdMQqV<lQa@tCm6=etB5c%Fx4#OgjrzThb0D&2c&sJdD=X}9uefmIVc;FsBfZ^0$L~@7Jb`8vIrE9dy(02E=AQme*vlb%@xslteLb}2snn*^{Cxz1KYwiV6kdd>N+E6kWzfC(J0R;qX^nPfqoW!*(!w4oyuPBLe%XZ7M%D|PwszFY*QuHgk^=GBrT~f~v^*eDvjm+^CUf6WW5*PHLPuyk96m2k)a@T!0D!xi&S#KP&*#^RtI4XV+FJvK;<Eu*^pDkELoyK!(MFd2+O~i<zc;4^3)o-+1rvkMZkVs<@1P#LxLE=a^YaN*R*@?VoH^_T2PS*=b+)HEunpX$tIXeqZS_WW*rE;g8E{)*hdtGnd5@oRuV>%#q+nT|Mbl_CnXOzwuxp|n@=7PncL0m{m?zo={4Kzhsszdnla3)G7{+CZ-id3jeDB5_tvs>fIZpPlemkJws|M}w6n&~BBO1epDqGV7G-NAo-Q)2_8S^RV<G*expM`8~w`qN$ZK(G;OhPW7#=|}V*LUvuV7Ck1bF?S+r1%6I&`+D3R9bVPDM|Y@HQeKdus;(<$)wrd{|&6KxyA=Z+t#1Do%Hq*X&#fL_wZcPJ#eVriQ#@&9(`q~>%X{Db`hlg_C0$2WNCXY4!t^G%&(^BAG-bemkQ9|vg$lmZ?;9|>p1yzAFIs?dQWU5mEaxyU?Gfkn-ZHU-^A{BVB{@q%B}7R?qct2Rkf2b_@?0NRrQVs??1JyNjv'), ('899ac3a9f2c70478202f8578c52b7b8890dbc5aa', 'github_review_risk_dispatch.py'): ('31324115c90e10596c52988034f3c1b390bcd8e9', '6dea76e198a4b93739d4479ce61fbc7265d4248a9f6e2ebccf18c754ffac7dd1', 7725, 'c-p;LZFAc;68^4Vfn#pwqzomeGyQUIb#tsl+iYb?C8ad&O^*YSkcBZta6r<IlgoeaF2HwDN;>JBKG+hmz%KUn*`;9^p2%gu#ygS6A(1?NB#C7Eh(8=MvKNwM2S#`t<i{P0GjhwbyL@+Lzh^<7@h3(kd*bXFC>|tB)5&14&Ltx>eBuH7j>PPVNfJm#GnNucp4sjo#G^@Ql1TAHBa<ANd|)Q|QS3}441o)$5fO5b1_u`A5t9?L0U_9Xo@T&@r2HXfAS(+P$K#KAnvsx66h}z@z+;oFT@s_nlF&FD92gCWcW05k6i31{5G99u0jB^23kgUWXIBRS=imYylD$lbMQ$u_Lui`9&5n3`o({C0GC@R)BGDiNK@xGbcCQo{U<X`SdWc>K$R9ky@$`Z6nCuv+6I4UeN1jXuhG7hpIKIEnGf<lE6MjsD1R3I3WHjR<P6wJMq!|q&B}qwCJ<=2mu3IkI@O@Bxm#jD<5OF3&<R=l0+2ny|hkWO2>-lJQKM@fRUdl6u0|Fm!c4yyPruyzGS{F#IN+Zpc4QJ9EjJ}Xts@$&44bRpN=7K8MuwYitwVQ5Z`b2p|cM;P|`tjP;zqG0RAeRz^^Ao9gJp+4x&tq^mkZ&;XU3<NPKV%B(nFQjP@Q4ki@!$Vg<KO7`!<+Fx{mJ<EkKdTzym|BKs`u&NjnTjdm+CzRNa=Y0`^RrJ-QX2j#o!OhcUWiwISt1GAMN2bVEdGaJwzG@$Bc0CrHDsxV+uYKiGW5EIL4~o7QDkGnWS-w8q{Ypc~w|($Kw!V1>G@^A7k+x*Syk<zQAD*k=Vhp7+fg>i-oYH1GWf)59qB$fGhbJIj~4c1&INdGWjwYtX+Sxnpq3qb-bVayVYV2O0m4v(gV$aH+*1m%Cg}{Wg-Kpm#Ym>ymjnftREJ(VO9$_&cgQm)pp~rZhUXHS~nMGtGVs3t<CJtzjr*(S>84lz17y8;qtAsv^LIa={w8W>VCbjH})x+=5vYSe)ZO#`}3^}Z2XzM^tRq9k+-on`k1BXcpH1UIi<O?t+_s}T$^oO7f4HjmK2}RJyldU!fnpegl56PmQu*!TN>p|eH~rv0}aC>;2)4E2_{t@V#<jjB}0DYVV%*&;1euiai~&Roa7lv4>VyDOhs+BE0sovX(mmTO$t``)^ZDWwziwQmFxUw&%waP$wNcY!td2Rm}2IyR|{wME0T7fb=j6TJz>1{Y~OwdI!1F84B@M5d+1}vg=H;__mi^*w=2BPU)uIu3*Wm?U!Z($FPvKke6_qp_qpDoTz|X#8Q42F4)~8YF>X4ugbMg~mC1)XSf(49vr(y-h67lts%niu;eiZr-BFxc(y7(YARk{hax?iKSwhiLB#<mp+zomzekUU3nUF8)SwRYdS38nCihNyCufch;9ulm7K6q5$5raX<_QXGkC>%DJLk8=Yve-8w<A0r10i>T?#y!irn$(r4T%DY;f|kN8w4%dwREQk100K(ak+5`6Me$k_YQ%Bf3Y=y&!ZLZ?TRe-aYGU?2VF6$f|Dq{6w3m(2A--T9O<9&r?LXI5ZSB%tGzw-T_?cqq$Rr>$NJaoC$22_hGzFI>P>PuRj)Z~$%4wAv1qA^@;yE`^VKCCn>H>r-Y?uMA5=X3<s(vEapamqnDsG_hoI-x5_bPT58x>URpg|2mh?OMd*4~iUbe}Q#8p~fJyhs35El&|87P(i!P+dP0j9jeU>T=^MEAJs{Q-~9Q3p&M+lmSu-iH!n#nZk#qqOJ=62GAQtBv;U{!r?VcEw!%xbEwiU2^(ss906ceN^bh*brl?vqM6Rs8AG3;ueD<Y?#1^UF0p&5p?CrN0pk?hi%q;;NG2yWq9MiSqqrxMFJyeP;nL;Ds7SC%`)i=H-MS|0fNv_Wj@^zD+aY{%4V~ePjk^UrF!#$^uaJ@Dc_7|B{w@Jb#dN5+_9TIdJq9hrM2TG|dx-s`%0}mQRf)O$U^mxd)5sqcA50@a*hfRYpOQD1Pb`zniP#z{_etH_qLThOt=jL__6*hPIk(Fyd;88DRO)Pgh0JcfwVZ_lm2GpjQ$QtLnc>bcEX{|0i#%o)atCndBC6|US9@*kLKEy{kCgmvS~OIHhW;94wf&H^$E;`eHBHpq*m&OD*;dA%<J#H#b)1#uzlQyertAw3IO|k}FWK*`*+!%Fm5U~>yb5CV9=nd(#vLgHVCvGN5W4jU8cHZ4CCv?uQg%+9)Ap!#t%k|VplMyXeAo@qKDD3QJGvm)X-iYd)({P`R9yfN(<$8bxfttdhq^~-Zn`s`l8@DaMr~{3y3YgZEN?VCvq{@{+#oKM(xfb(X|hjWrT`oy)e2~nA9>7=`O$B5XMVk$qLtos0>0d`7xG9!ZV~$$5cuU>O>etyc|u$7C=&G4+hw<f9erhK?ro{et~NULSxEz%oaNkJ+snBsn)(3O{(0-TSgXnF*UI=kMf*hkF&Q>ELZ`l*TW(v7nd@LmUo>3)m6|mE!gd9~BF|Kf7(>By>;_T*v{RFsVhjm{0xB90$dLvI-YB`RGyv8POQo79g1OLWfK}n&18o1mq!<T4k+lbn<s_zY+AgB;BLj5%o*fhH{?vRn02BzoHR^!aQY;ZqzS5q3{jS+nc*mS|qknJB?wqAv854lec|*26RDq_AV?!=pzJ-nr(~WM*sOm6Ub3P^WuxxHa)l{AtCw{hZ>$G5IZv(8KYA0y-R-f;Xe$a!!qLmoyRs#3vb_6;HyaPT^6Xvm+ELUUsqC>jFakWC{doGK~b!mS!_p4hgoZJ=292Y_sp;y0{Rf~k<LPb>}`$iL_^@(#raLaujtI31vdN3wH1tA-={T|XIY}9?t+R+j~FOw;vAH{A$&<yny62FkyV&!3Wz}U(Ju+L;Ya@5$NXrhXVas+CN#ke4;LgD|@24U-{JIAuM{p%W_-a&&tZCbw7sDo~*fU-Ix12^p?umJTGfCK*n)QofQPI4$(Smk8(%$Zm>8{2Ihg(K~Vfj1=-*sEls%v!aA>cs}=1&yqo5D!8_L%Rz8M6<?e`elh0Cyi;69>64$f?W8Li9(}`)lUtr;g}F}CS<}Cc)<o}#3wz-+9VOaS;_zoe0KIf>=Z+EYO@jR(*|B>M*FlE8;pwKO2Cq={{;m|gzK%cU$%LH^2y$9Eh*J)F*J*96P(hkz2)StOIZ?O1w22PA6-BO6`McR6czC8v?nT5WUGHTvTV4-n#pR|0d~BqUT4%<0$+dVQW%P72sVm&6EcN*CDJ&maOnr|D^tyXR1!EaF3BN3(s+ypS7yl|$-tFTc7$K}QW7sa`D-qFDV7_3%(<YZofm6o27@h6?SruWE_(uDr=99$b~=Tr4z6+_`Uf+MxQz'), ('fe0e7fc84dca8afd30d4dd0ae932da12403e96f1', 'github_review_risk_policy.py'): ('d8380d2b92c28bdaa4e6590d921bd357012e4fa5', '54c824624d0c5eec9d14b263dc1ebce42fc2807c05f3299573b205245c160d07', 16491, 'c-pl)Yj@kYa^LkUP^G6=+Lb6f-QBj{`kt$m=|o-IawR#*HaF#=C`e*VkqkgO)~5OIof!ZmNJ@UBY0j<%f_Mz(J%eGp-5xIQLYasi6QR6iS;z%jC4%`(Cb<ZB|Bj1r74ju}6=tvV1-qWIWw=^7t=4=KN(TS=Y{@e&wqYE~EDTthL}9RFVVvd}%MzAtIQxO$<I8yc0~0*rzU0i0m(aco`R7*hIp#w4*wthXt8KYh^PYakMUVMuDv~=t>ao$d$37?G7Jx(;m)lUvFo~I;XPZQX+0JR5`#~nzHkTP&a26y{#DfgLUx{Q3d(u!I1Drng2DuRM)ZcKwIH7=ckHs8L-lAD}WG({{rWtJ3)4TP9B+dk`zhsfW;E^Pl*03CtJX-brEaNisagNh!x7%tl&s*hLF1Y8haGNF~1EAtW4U?^w?pykqA4I;CT$(Py)dD=uw`Qsf?N)0xdhK2g*(qypeW@t1bk<?E$rql&qKCxwXgRqB0G+$zcFUW+9{zL$(*$>dWSfQ&?}+w)zd!2#o8Mo3`0~@y*MDqxTi(>Yo-{`d`~T(l|Aeug)Bo`0xOaSX^mVYemlnAkzVoh!^Vc(2>E+MAsE$i_J{^ys=lIAwI->tu-uZAgr?(g5E0>1<ROvn+Ur_f?M{1F|3op*x3wJ)AT;YqKk6Nu4Y{=x+k0KU@F|t7pR3WAyy0XPC1#GZPKv#bOZ<juZz`!tl<bT%u=d`@hbUYuAh8N!T)IA@+qs==l2LIX`%Y$}LJuj0$4rCH}@-~bj+3c@&aN^!-C%@-Go`rY3+D&{_?a~yk^l5TeryAiXx|7u2Cn@37EbXO{AM-(#h4znWf*ZyeUkk<02bQP|ky*YB6K@#`5L9m)qy;oe<m6z<(<mvSH{Dv1l>Gn+9<!WZB|;kI>o6{#9T2d5$*t#P$?vVlT!3OMaT69zlxsP_zg`e}dwLBh``#fr_Vw3rWW7-e)h56yTo3YC<grHsKKnobA)VbestvNi6aEquaET6ohpM2&#{#fr57>qUjS7BR4EFVcvRVKo_Ptw$u^$HopCmE9=~_bNz8j9_AW@*({^YUbS?7zIIeg__&1cSbX_gvY3~$a{t0Udv=^d~;#Tk=(`!P=LSD>$)bXW37mZwgzTGyGW)SMm~7@7KkJx@^skxE<EUnodC&0*H-bO)yEBQUm;B_(l2lQVbn_R5{kOwY_6-2g`Zuui8bSW55KPiqw3D~G@pS-7=<KOoggdMu+*&LF)(1n|zr!;8tQ8`qn;vl(buZ*(!4x!%R_tpzKMAGs4yk(2*$M|1D`VhAHASM%}JP4!qb6x8+jjXV9rdpnu_ett1&tmVD~gv?<Kjc}*lbOMi8ue{Og;dpupix1Dv+^e&j%lgcz`)2IE^`_(5@80#~VmxYW{%Smbee;{A2g0ILI9WLeOh*v#6upBNFOQD@6^us=u1iMT>qi44+bl&=vtf+>iH}}Hv;+Ss-jRO<?vGy0hn{4GUJy7vWP-pc*fApj4D3<NzyN_&LQe^>$lmgWHa|>>wzH3rz@oQ2^VZ<V942-Gvq=IE4w0Z3KplsHht5iE9CBcNz#c7w3!>j;zY}m?Uj&=MC0K5EdO5y2L+VYT?Y((v5#?+$0yp4FOZHb=In3Nwm#78y=?4^yc2E6khYkp2dO&3UEIJZ1*3eG31<#~qJ>U^v!0!?l^rPyN#K#ns1exvXlPt{yy&#oMEm94IJ`mv@Xrwi#SLT6M&XQXm7Y(WQ-lbWBEgn;ww$(OV0LOTRTBV7g;rYHU8U6{1own3Uzh(sRl~(^|mTuBEMT4MP2mnx+6)M{)OKny}MY@WT&m}^<LYrwy&*sCcv*Glt>07;EQ(z!*2Vw|(nn6sm9aw$?g%8TO0BN+}hSA8@4>sWP^+CPep^NY6)g}Utgif9U*k44PtgAH@NSrV~W2hK2W<Y}hqzHcbi_}Yv#_Ut>M;I0fkkiZuMZiLcIt2fegB!C1*Ar00f(;LD<zCrElvKPR>@c=c5gaTDACTW}yKTf4O6rs$Eiib{kk)MwiYCEHoZw{lnc|G#7Mx7yqbzw$_w}PBxYaLMd*_ST!5*3wr(5-U=Uev87we?hO+A?z(A*|V-IDpX&Ik{QyabGHeG*=35jz%6N994Pa{{V@FbaKJauBDAC1q&lnYNN~2(4DYuOxXgT*pcis8%UDB1tz&V*rR*#0$3Pi%pWy7TOlmqWK~!bd*s!g(9iTMWF#-j}PF2LKn}3E)|7V>c&FDEIp-{YymZDn%vG(VHHAE)g&PV%IIW<AUJiJ9RxB53HBCz<KKk|X%Tc4J!3AEic6&QP|(AGmy|6H%r=eqJ$NfCn4s4HsTFxZ&Q7rL<F$cjcv0f3j=}$7HE>%V*c}j>xqCI!fn%plCJ0=AAqhAm8&0Z}q4O~{zg#td)+sgC;R?fC3Px>RrX57ms?ef_M_#-1ya7yUwJ6SKQ{c*LBElFGC$12Q=)CcxoKv%Vq7c$<&%sI1I!nfWDmO`{^j?HIk}rSNA#Nr(=&~?lKBj0ed<Oj#aPW2=Ohy#@68-0($~u779;FoYW;ExNweh!2J%vt$Uei`@3U>zHn6`TJdU8SI@fWxKo0Z#eigriw&gop_yjub792j^8j)#IN^|Q?hcu<0#{N+-K?Fsl>8Fei|@z=Ui<nbhzUNITi;VOwafQ3Kb0Mv;1j&e;3F2PBKBw|-Wm*!FA0Xi34l)zx7$&(wu9Hw}9Nzeh*5THc-J<-B(oDa`9Cm6XHeNbQ!(hj_m(&A!3j_Dm(E;wN#Sm4JDgcT-)lnUX>R4JLuz-=Hd^GpWtge{UJ(mTC|O_Axqx5YiRwN*((G|lAb!b)5x-U^6xc92qjYCp1Z8(gn(c$A>7Ia{h6a4_J2b_T9jAA>u#<(UWr`D^9eT0nIA56-F&VN5uT1)$bwxwBeIFiSGf@;x;BKx**)0^X-H;%<^H6BZ{K1qJz*m&-BC9`qG0*&<)AdFHUU5Njov1y#<!f|P+)r1_xqeAHrkON9;G#nU4VKB|IXqvrXXi+W~Q#C(c*mCh|W^8dihm_R<UlnQlXYIvJ(J&3M(%477Wt+><TU^5Uk85p2AiM7Y*nH;b+7?@fT|JNmk-u?~kGZ)!TOUsI_z^n7n`|^PCmnZ|ggNfQM>;IKlTOmWM*{dWg)5@5}rnK}4rJy4u+9rvXl6XB<R1`V#2ZV}Igdt(HBRy-D1k;?0m@>l-W!Xbp_d2L!ftm=XrzMnkR-|8=Du*CO&7~j?A-de9dUzKXMh-oos0bE61Qy(DaloHXRl;0}S!0!Ux4EZNGEA{OYFUsw${sr_V4kg?1)Kfj%cDF7T^JK`EDqfZkHxG7K)^N#P-6i5_fvNCyxnm&Q?vJOZ^WX349d7Suu&QQbX=He#bt-jAlTv}z}pqv1GPVcE%(A$u{s5yBuWTs#N+(~|H{f-{?p*BEMNgkzAGwR+*89SIgd}!D4{r`jzecsy~0~5TmlHm_CQv`V$O-(bqZj!bBrX%1F8}5@bmG@Zn?ly*+B14P-*z}{@CNl%omyb3?`t{22T&SZ~y)8ZG@lBfwx8Rt^<K}CjcneKflB-{djuHj$i%@9Xc>Go&jPWOMk^5fDm_<e2w}Sm;cfxFP8o|?XR@2^;(@LjlztM@(e&gg@d+DVlb}JV+bSe?R0TN;)5q|vIGty>&?ikksR;lR?vkvj)!)|EgW#HI`-ZrtHnO}E&xfVT{vGV_|R@w+d{$}y6M2IVDtSf6H0J;v_!YTmNdAom9Tk)oT!$9hIK*qWJIjmUvST_dxQ)~5c9P%RFrr)pt=q@e+9r*L;0ZGA6TjaT@rCW-fvS1x3H<5kb4UlXbujn3p@5{Br_{GT$xveA}P0`MY~TsUpcEdk+PY$F?hF(OJI45_m%rdl(oz!Dj?Kujnj77Kb%_n*Lw3bxJqdtZ=9y?#jx#aK4bx^<DPE-?D>!Ae>KX4LVN9i9ui<?yNsF+nheljVpo#7;$AmolLps3DC2fBvzSBLTl3X}mgp&n(dS_yWtqX%R6+)*L8sH!U9ze&OIU2hSwY}8C{PO|Ydd>Y(wWW88-ptZdUR5GAUjw$l&CsIdVHrOS#_4J2P%{BUrEKvMu*Ay#1-}sp@M;$&3ud^W^GnL_b5+11^4?PE?0Q2-P>pTXrsFA`=0jiIYMQW&6BKPQ$eUq#vYWShOW9OPlQOaWE&QD4mJf315jEznQuEQr=SbbYqejukr7ed#rT%R!D^|3s!v?182=nQSvkH=pHTQyOT75&wLs!<%8FtnY|;Uyh{?LP=+qMp6cejV08qAv<o!_OOvgZLfw?1J%3R<j3#F}oEkgGqoMiSU@UZpC8%=$@11$o29n60z&R>h<Pgv)u$Bw$aeFIG5^ua+UhYEv^4-UeVYIT*b?-4H_OeR5anMc{dJVLLLuIaHKinI!7PeSV9ypeUQrj(LYm2Y(M^{dKpeahACDH1yYvWLMyBOR{?RZ9A<$jf0;c1e|j;74UV*r>q4DpFwQlp8Xc%_1+ve1R;8WYue_#AA@<Fxnz8kAc?%A}~{hjwuhoF%8%vjPcsDs8GZVkGVdiV#j5|mDb`h-XBuh5Af^*j{B4IbC@7$O`QeA0zgzdeZ0?Cc~7;RmHX;hCpdkS;k!2X?W2pOD=4RTs%is!RvOA6;<TQMDF<2Ek<&)Lq#R}v5U15NMmYdMKE*#}*CVOGQyVpnNe`q2Pm7j)R^sGS(h8j=go6(9#4X>+j(*qGa$_`(7fLS>A*!T^RDGwoGpMBr$#??EY)e|W_Vf<J>a=hRD1AYZNVW9o>q$LDh&kKJN{%Q(?;bnuzV9D@pvB8{B~=GXeS4+K+Vlg}z?m1xlB-hNc8R2-Cc@l(sj@dpW~yhbpwy2_$2<XIpsdM!*hN#61Zj+DR!?;w+ybLNwTP8s0oP^~-fKKlyNYacDfhtASTw525K&K{K?KW1{t$+;pqgUL<U=HYeR!!>UavB95$ot%DgaA|BG}f+D?vV{;5wBe+V2NgC;KDdna<NysSuG><Q#dfqgMPU)~t=OSr_nuP%OU#>(&bknuP1L9r=lF#?|G1_xn+;Q5N#R(*KXRZWJZhxK=#-O?WmSYjhNOH5-yrlOy8HdGvj<xlXR!CR5qSOYoj57@)o0pMcKj+WudYmL#KUY16(hA3jREeQzm{J^z3)z^0lx)XpmH`?iic5TP&BMKjn}FdkSvgAkEz_3c8uUn+GsCu$P78yxHXsm?y2L<_8^3U7Y3N_h0Jvi7H1qQhJ)!t+)69;!)I8ie<yu$)ylj#qcIF~nh1nuq=atwfk%Lv8X+8Q)*fU+C-49A1F45QOx>0v=X7mC8?{J6NnR!TgviVH&`BDT71Tcj%$$ZwXp0Z+3HiJ(*HPWV0&0sJt`xmsEAI1sTn;@Z0Xp@B7xXDQU$zSU(z2wPY&#fiRUv)mJK^r=Y5qy4T*AdiOv;%!CCCwaWMkNNQ-Fa*-mB0tAt-3W~ceZ+zuW=ely^K)Dm%b#ION(?#+1o^>8BD;-#<(l2|doTS{ViQ;0?pt`0kpI82;@*xA~S6~gHKF6E!>;`rC&3XNcf~S?5;BOctMXmbhWTiT>@zTcC+<iB%?6bGX1%|tC#%J!;$gK@FWnZea6My}!QTht7K;F^sCW99hYm}#0N(C;puG2ZFDIu<+(gl?{#ZNO(v<zGHQ0xR#2&RzuE|j?r3o`WlG4sl|Y38WA-<w!1gcrcRt{S-X#qAP1@s4c*ngeY+mhAeago1+~<P>GlGH$6YtV%((pHc_q3E4-LY6yH(5eb;P!h3Mc5g#?aRkNbaRH3Xbv)L&n5j6flYyQDL6MPO#$D7u@CP?4SayNyh2~y4W>}Av+SzSiD-{eR%_2l=02fG?FQ!(N7bsGm#qM||``%A5dFa8h5<G^F1O_E3znbP-9$hVrg7r6j&B1TpBFpC{4?qqaE%7~m6B#L@hIRxWqv|<j&z>?QIMx_doy+r9V>&JllweVxzr($R&mt?kZ!Aq=`25G5nheC<Tj2=bTbdTLvr9@KZ_Ix8nwHk?nH*osH7g;9T_+a8*6R?s$>D4nYSlW6so#IClqsis<g*$h>v+?=42kHesgm~j#X_wAKlpyx+DWChuUAEB$%}BKS!JM>MQ(uQ|s^N}x)wS=QtNV<znl<6P^XbiO?oFoN@Mivcf*-7SzfEq?$NIxu;OhwFsYh+Nk(!8y?MIg^!2W2bL{9-n1wFNj)$f8HvnH~`<Z9;r=M8Yg7)StUQhf0azk9fP<vx_@EjJ_sP$p(ipOdO>8j%&<x7fEcAT;QSz``movU+U6!{lfzPK9g*$YrAXN4EC>29_ptp88@_-Gf$#aj<6(V5^p>CW8@0om#|Z<zx0%x!@-3sBx}ZLLJYwCog{RAp5o|?q#b7(YLJCk6XWuD`z*q;S=#Btv7WqCvS!qB|91f?Gd;~5cLd*Fl+*7)Q4Oyx(GKIQxEZE1lJ5D##mJA!kTao_^5pt3}DreY>%O@gufAAqsg@kZqdkf&t_`Hi}B@n-Zqt}H}tU<#iTv!vw4aO=^GLgZbAUJg<$d&D-T)6icz~x@u?Z5!ZG9|wML=5`arA*Ug-m|&l?I*F_Vm;rT%mPOfp|$h-tnx)0_zivl6Vur}R`K8;VNotD;+d(V_C%I_do!oPi68AM4E~H&gJ2rl17JQ+MW##@_65@;g%Ve*rZgq|p'), ('fe0e7fc84dca8afd30d4dd0ae932da12403e96f1', 'github_review_risk_source.py'): ('0295ffb725c3ef29f94fbc6a644d044f09f93847', 'ff82c6d68706560935d5968979167eadb625a3701218f4f900ac76f32e6973fa', 8177, 'c-qZbZFAeW5&q6!fvR7q9?dv6(|&NPOch&BbZ1K%QBE$s$zUi7vT)(s0H7UT+yCC(1xb*SoY?72d!F$K!pmY`pWTH9gTYEw+K3H%BhA}t%@#|R?Be`Zutem#(rjBOW_E%psXv_<DHQBg;!cWtwvDx6X`GAD^H#7WiPKalc6}4A*jnZrI43n*sKOLUkup;dA(<ytwida8kv4E7HnPZ1bW)Tp8=eyJMyP=0g~4<8V!bPhPwa<iJ_}e}nH_MIq_NC&fGivF*#yAKTBI-mYcb1#!33Cvi)5UJz##CF6`Lv*I3F9KfqEl$l1kVZG?M*LtOHgGl}W9EIh;>LtOb(3SJDU-dSjMUN}(LOs8k}@4tQp83G&X?h1s#S0PP7DgDT=J9AZh4m8md-Z6&Z##<wyj=|gWY7<gM%WQ_A|Whx~&XEG}bW#BkyfwpPS?%Bj92I;j18R|{#l-*$-N}1m_i;W5D<4KVlRiwNm+ucgDtJd5~&e6=gEK->~G^c%!!QYbB&&f9~<HYEoGkpo-M8IQrZV8me$fC|rwRQ#O7DRlSmz9|)RVcec!ssp+fj9KL>+w(ga(Xq1*ob}q=f8N1@tX;crvI40_m`)q-uUWj{(f@7qt$qI6VWyh@mFwNVf=p*<w3mJh|M5i1F*i_N;_5}EAE<M9%pt4K3K2YAb_Fw@1e(EPiN!h2OiyAUQU0aTl_&-=C`;r{H1I@g&o|=Eq#L5mNbw_L7(NOUMRM1@cjTTSd3TaZ$Zq6Pu@*0CbRPiUo0o>WmXU+w1`!*djU!UzfQypD^>ETDs_Ld`h3#)ZjT%E=R8hdY>GtFE*jhk1zJhS!Eo<!Zu+99MJ=)}avD5jsr`)WK}K2(&1XZOiM|6dJ&#<J+#sT$xyj?ZSVG{Y!e3Sps+l0C7@k?40iOUebRL&_2T%af1)D5l1&AaN6B52)=)!akQUHcPkV0gq1sG5@K^kI!5zUR*LXgQ^8qR$!(ro|%u@PrX8#QDnuh^`}g}omCbOkuz55x8dZXUMFe`FC{oM6OmSg8PC5{mPU0Pqr^TNbOeG%8jP46I}T95N<8C!$1s6L5v@F5o7_v!G@AkXwvoVedrgfdB)H6T~Fw^Y3lk`_}JAfak!T)w9*{VrivOqAavDg?b=aX|Al&l;?=Y>J0R0XcB>p>s{=&tpWS`GqmRzMcR670pLA916%|cA~Ps}#Lo9R;5Z_qcDz9FN`gK&wE-;dOg&8rh)`AycmW2y;|#KpskHn4^*c#*h*d?Ud5<9b7nueONEV`vu}OBk^>ZsTY(OS^Az^dT5;VI2-1QsOcCj#q#E1FJx_Og+>J-+^rp)F~xT%8Nvj!+Pl$TOg+~<(IdclBud8sV)+gw)1#h-$GrwI-`hC-(AX!sX~;UhPox;Ugh;rIOhX}1NKG(|HMinm{h7%^ii$gw{=vj@n`$350Of`Pj@mEb(UkMdz$0jXmBi%5)RrD5VxNt^hjvlO6MurzxRh-f8ra<M;*h_qYlh=_}DS<9)4C4~BMv>Ys!JeuDu0h<w`SJTx8elz=VHh(`G3=f$LG5lH%$pf*lbL$k3y$#Ri1CuatGkZ6_nqD|2ke=hg32qVK$(PLLE53w$G<iRMeKm39EwMd3I#lx>E;SpTe*fFa_=1?2&UiGwo&Yn8c{E+kmmg|ouvA7M0B3<D*#k68f-S62>TLjJFmx<HVVMCi+zJ3BQ+s4UBwfO3tcrVEbAflFq;&po?6e)ff+C5Zp3=X&<|)!*(M1N04h?D*+LI4%ed%=FUwXybD(>mprtN%wv*Pnh9-Yq@jl~UMLrdkbYV;54RKG8G>j5Ji_7G-NLa;Z<Z`AQC_!{)6Gy(#&@ASwY1}<leP6L-M;7k8pUH{iG%Wdr?HlxcJlDgYF9R3eQY?Ax`MMPT)9c>IibX<N0480xm>+#j)e0e<qcV*P<0EN2xff_Bh4tfCp=&1b!&;ff_I(!N4an~NCHibdE6SB$kA^=5N9D&r%CAN6!Ug6@<uGI*^_Isu0vO>oo$3!=a#eBJ%Ty$a2V%|4H-0uqCI@;Z<-M%qD(q+_C9j54>rA8yyj-DN;q-JTq?%cP%%eRLm>a%pTz;rtYn*-}_`Smo4rn5IS=OS%+Ke(mgr{73D`?hOTSbZJYAw?j}i@ffT`auRg={+@SBH!qHX?Fg8*FHq$IH-K&I9NiNn!p#j@(w^lh5c1lzR*!yN=K@tJ>R2?aP>eJPuKDJ{GxHhzB!MeW1V>FE~72qQ68{#9;beN5<88vBMr>cDtfO|vmbppYRl=5Z6Aa;xVN;p>58be(*fJ!vj?O19m;hug*zB^T5|hPcP8WffzbnBeoI{iGE1Qc{YVZx%RA9Fc|<zE?HOtx_dvt~VeGj?+Ytw>%9Tip+g$z%d+3!9GHXehp~`ht;)@!dwoisiY%37-ulQbZIgVCn+ns$6=sc)ql{RGgq{tzi8YVD3YSdoQd8NdMQqV<lQa@tCm6=etB5c%Fx4#OgjrzThb0D&2c&sJdD=X}9uefmIVc;FsBfZ^0$L~@7Jb`8vIrE9dy(02E=AQme*vlb%@xslteLb}2snn*^{Cxz1KYwiV6kdd>N+E6kWzfC(J0R;qX^nPfqoW!*(!w4oyuPBLe%XZ7M%D|PwszFY*QuHgk^=GBrT~f~v^*eDvjm+^CUf6WW5*PHLPuyk96m2k)a@T!0D!xi&S#KP&*#^RtI4XV+FJvK;<Eu*^pDkELoyK!(MFd2+O~i<zc;4^3)o-+1rvkMZkVs<@1P#LxLE=a^YaN*R*@?VoH^_T2PS*=b+)HEunpX$tIXeqZS_WW*rE;g8E{)*hdtGnd5@oRuV>%#q+nT|Mbl_CnXOzwuxp|n@=7PncL0m{m?zo={4Kzhsszdnla3)G7{+CZ-id3jeDB5_tvs>fIZpPlemkJws|M}w6n&~BBO1epDqGV7G-NAo-Q)2_8S^RV<G*expM`8~w`qN$ZK(G;OhPW7#=|}V*LUvuV7Ck1bF?S+r1%6I&`+D3R9bVPDM|Y@HQeKdus;(<$)wrd{|&6KxyA=Z+t#1Do%Hq*X&#fL_wZcPJ#eVriQ#@&9(`q~>%X{Db`hlg_C0$2WNCXY4!t^G%&(^BAG-bemkQ9|vg$lmZ?;9|>p1yzAFIs?dQWU5mEaxyU?Gfkn-ZHU-^A{BVB{@q%B}7R?qct2Rkf2b_@?0NRrQVs??1JyNjv'), ('fe0e7fc84dca8afd30d4dd0ae932da12403e96f1', 'github_review_risk_dispatch.py'): ('7c096089b5863b5cac5b44138cbb924519024cba', 'ec9402f9a712a951cc66c51653867e754eadb0a1a92c3a0628b2562ab1445847', 7954, 'c-p-gU6b3k@m;?HWja&IL+PBEzVuRc%1FFBCOT0eDc4CS<v=8KVoi}ONS-Y_{_oiZ_yJOsE*WQf54H#_b{G4-3r*A9wB!Ms?$R;|36Ju3B;#x!M^A@>>{CvP10zuql*b)Q3UVJ659RL0{J?^;h@KhY>^WlZ0pf|XJfDq5o02m^!{;bq-;jhoGfo1|Xu)zq$$Pdtr0F}I&@AKWGmUj}Wc-Qg<hyjIBVY(rA{vvFkMiKa!ZK!jMm%7GeTeb`=#V^mN*M6U0u~|qW0@BuWE|N^dGr(|I@vfRL6$k8NjN$%8WQ)xAbXx3NmKwUCEN=r1;AKHfXk$~Ii!FGHvma-nh}HC8LoHZdd7NbI7>qF9IkjoF+}-D3am&;njmj9D1f6Zz1cW7f*jBVax6c@Cju7<-T@u@M5Bc47|0c5MDll0HXCW0HWGaK{=O_gdcIGhW0rDYCP~tQ7EzkyBMB4If(EhRqy}o1Bm{$d*IOq19#y|Nt55`KQt&kPvzR7q_7oL|a_37m`lx?DOXDaw)i}l@0)Ot}!F)7y@!Juw4uBesMARKGVqAV7qa-?(#|At5Um0<R@VP#k{6=<iVW3@hkhnBO2V}j04ZT^H2E9$_GmT=pi<#V#%Ns|2NnQFu$vJT2XI#>H59IxQlz?FZf1{D_m>V1ZA#;%5EJ%-86tgkc{_}5R`V*agd_Db}Kb!vi>1+M#*RMa{46goJn~Z!gzCknqN~imuKmAq0jlLpw0tO?Di-kIX({P&N(jIOD#*veB4?Y=z3CFm3syr7Ao`O-uX+Yx{pfOql2lLTM!D*7C1SL+!Zz?tKq9jDGLVGQfcS-s_X=&vJJpr<(INbqSbi<s1#zNSVu3fpyM>OXu6bSwpIj~r81tA2t3Vxc6Hjclt7skqWEcbi=!CoyvD28jVU62e|!$+3ntQdb1D$)RYZF>Om#xnn9e7iC=z1g_4R;KIQThF)ee0O1Q)XjyxH2sa?Egt+w%XO{wy|U@rTW5jW_tx6*EPL%+>xKQeS(%=B4kqbbgLt&xm`i`Tb%2b&FxT$ZJqLmq;z=}X*K$2`?VZCsn8s3KtM?XL#{tk9pu@#yG*997ia#!+JflT$FgZ{8_zjIqCVozCB|=Rz2-pXNRD$6*3Na=n5WFE0M`0WLreG5+V@W7tU6Pdr$qzJRGmKSTvbG4g<GkRy2sag}M`OJOJsVr^!FH^l%q1vTJ6qHQEPUIKpo)dRu~*jOM+EJ!^~u&ZJtMqzP2YSAGDdY&1mUM+x@cqCm2Jt4`@OXRv#YGmUz_GqGC#P{UZ7q#SJu4+wpw4Jzb;P*)8DRt0P@zI1@<FVjE634p#c8bg!-{`mbu4EHmL=p7=R)2uapR6CWrvHJ;8}B8Cv}U0`{#EyvZ+Q4OvZqK(NU1G|0L7&eA+8QhpL^6(}&?oXE;J_GR+D1>-3OKrli2U{OOTMx&7JiGN7raI6rA2sX@Rb#6kY|F|du2tOrH2DW83X;W9dJG-C-$%S4?MY`#vVmV|1IF!sIVQroQ;*|uHwaIPAanx*tdGU5IyH;0~!0bcD0;pR2tE%Y1URO#F_=<WYWSusp{oFRWwGVq$DHx65Gso0XaH!!R7(wYdrQtEkb1+!~sfh7!NSG2RgF2~36pc`9BAz?QFz9J|a{&^GDzbpWD?MVy6!{a24O$hCH`NVf<tJ*y^LtgNtAnDJ>(!021R+M2k$cl4ujsyD{1v7@#l1)XS*^^mo~&Z8C|G6w%+PZ&cZ<tSo2a}8ug$?vpj?n4hU5$?rI47&uv>@%vKG`$W#3R9$1y2IZP--oZ9!X0UHl(GmOf={ERAvk6|E4mYMZx>b8w1kx|C-$i9=p%#|Ydj+DCAS-Kj0ws|EpToQisNDC#DX*;$TIxOmx%2R!*o#Mc#*uK%<K1hcfi0XWlXbFy@JRe-JU_Jr7V;j?SV2&Z|@7V3eeU*~#J85yn%>^<UlUBEO%$AaoW5NODw(}GXbwd-sTzJC<a=+dbsFxP+B_jSl9@uQ)GVFUn&V94L+<n?uob&xq@Tb9a0Tz8I$pnplK=G%?AK(V^k{kn<XzO@9ATHcQk*^M`bwGu^TSDoDu&@fj=xJv|U^`YG&jfH{Kp}2Ffsv9KNT5W4WGwgYfl>BL4bzCDwehOHtKLj06>xFZwiqwP3x_YuJjNeDKclOID3(bEC`5n#KZ$xm>s481B-x>=~R_nHdDsHR_eDx8#j#kG#E>fteYm36tZGh2`LlUWB?r5B|OYEGtN3CfoDzBZUbLD!m@1jFuzjStTg|YLNrr}Lt4Qr`30borh>aLf3Y@i+Lqma~OXFMmL8iZP_YwdQ(0@^6ADVC|iD$5FREff{9UXx&-FJuiNg<k5wdt8!&ND!W7g59m(Ky_M+Hh{}Q$uRFIzaGFS{hZ%!=iSuT2}JeDeaep%E}SO5tR(z;beAjUmYif-5=?Xw1db5JDtuKuPR^`OvJOUeWngqBGR6MBYHO=N%*=?87;Q@tsGV{^Rt*<L!vq_0ID&kpgeurRGM-MWaR&Rqj+p@4;UJGDPgu@WEW;|!I;4hxOuG9o=zexhbqjmDKAQ#fz2dUBBxJ1EIu0m1#$OLBCtq4N4Ys>ye0B|JuYKz6&z^Ax@fi_W>!rCd*Gp04NTiPW!`5=Jwj!@y31=NBvaZLAg=1l|U47|whg$U)ZmY~F9*xC=wKki3fu1kl>1B78{UjC5QD;Occple%c_{kf3zN_nd(K|>s1Nq;a#i+B-L~-M=I&cL!>qcXsqBLAjO?VK>A^eTf|#C9#nilcd#IYb2b{@^#$q4wYCK=}Ut(n0c7^DORa1c*A&c>K;G{R*9Zot0RMV6w{hO30jyS=<_GKc5CL*X{ECUgQY|8d~@NPILTe6KMIe<2-5J2ChyBR?>v;$Q9K^809MduNLDFyNcZ>OcQ?5X;{Y8W1a*pl-I^#AGLu<MmgZ{3yualPB%j6`Ca*H1UC)6GSVFK`rKrb>Xu_n-jf6o3K$1;mUa`(ATib>G6s+HpBC?mW{`P~kK_W?)Sj1@bZ>pjw;MAs%f&E~sQ_gop?g4V^aF6D<^M@*zmFlP5IG51<lGfiHYXqtK&c8W!_*Kof$8P)LnA(1HW^rZ*dC3Um_V^H~A8{l#aCZjh5ktt-AhS4th#+vkI2&7_(O1uQFu-&TMl+;4TGbf|%_$-!g2x`POb*T-h~z#z`nL&rX34TS0N@|%K^1JB}aL*{q&b5-Se-p*AbGR1#5ZB<NS!+0~N0X^O{FEMSDz?U024+_)w;A|A*CPWJHnxmkqO!^7zN*ALm5d;n_;^a^sX);BH3$+vwWZ+6UJHi*fyy9hNf6QgC`Lfc2U2<yLdo;W-)9hI4Q1v}*vS-!zyqCT7UXwGI&Q;HHe+5C#2Oj')}


def _module():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "ci_native_review_policy.py"),
        os.path.join(here, os.pardir, "scripts", "ci_native_review_policy.py"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location(
                "ci_native_review_policy", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules.setdefault("ci_native_review_policy", module)
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("ci_native_review_policy.py not found next to fixtures")


M = _module()

_REAL_QUALIFY = M.qualify_native_review

def native_facts(**changes):
    facts = dict(repository=_PRODUCTION_REPO, pr_number=4100, head_sha=_HEAD,
        target_ref="main", protection_source_sha="a"*40,
        required_formal_approvals=0, requires_code_owner_reviews=False,
        review_decision=None, review_decision_required=False,
        native_enforcement_qualified=True)
    facts.update(changes)
    return facts

def _fixture_qualification(*args, **kwargs):
    kwargs.setdefault("native_facts", native_facts())
    return _REAL_QUALIFY(*args, **kwargs)

M.qualify_native_review = _fixture_qualification


class FixtureError(AssertionError):
    pass


def _fixture_sources(ref):
    """Decode embedded fixtures, verifying exact bytes by digest."""
    sources = {}
    for (fixture_ref, filename), (blob, sha256, size, encoded) in _FIXTURE_BLOBS.items():
        if fixture_ref != ref:
            continue
        raw = zlib.decompress(base64.b85decode(encoded))
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha256:
            raise FixtureError(f"embedded fixture digest mismatch: {ref}/{filename}")
        if M._git_blob_sha1(raw) != blob:
            raise FixtureError(f"embedded fixture blob mismatch: {ref}/{filename}")
        sources[f"control_plane/{filename}"] = raw.decode("utf-8")
    if set(sources) != set(M.CANONICAL_POLICY_PATHS):
        raise FixtureError(f"incomplete embedded fixtures for {ref}")
    return sources


class FakeGitHub:
    """Request-sensitive in-process get shim returning (status, json) tuples."""

    def __init__(self, ref, *, files_pages, final_pull, rules_pages=None,
                 protection_status=404,
                 protection_body=None, commits_pages=None, branch_reads=None,
                 overrides=None, contents_sha_override=None):
        self.ref = ref
        self.files_pages = files_pages
        self.final_pull = final_pull
        self.rules_pages = rules_pages or []
        self.protection_status = protection_status
        self.protection_body = (protection_body
                                if protection_body is not None
                                else {"message": "Branch not protected"})
        self.commits_pages = commits_pages
        self.branch_reads = branch_reads
        self.overrides = overrides or {}
        self.contents_sha_override = contents_sha_override
        self.calls = []
        self.sources = _fixture_sources(ref)

    def __call__(self, path):
        status, body = self._response(path)
        if status != 200:
            raise M.NativeReviewReadError(status,body)
        return body

    def _response(self, path):
        self.calls.append(path)
        for needle, outcome in self.overrides.items():
            if needle in path:
                return outcome
        if path == f"/repos/{_CANONICAL_REPO}/branches/master":
            if self.branch_reads:
                return self.branch_reads.pop(0)
            return 200, {"name": "master", "protected": True,
                         "commit": {"sha": self.ref}}
        for policy_path, source in self.sources.items():
            prefix = f"/repos/{_CANONICAL_REPO}/contents/{policy_path}?ref="
            if path.startswith(prefix):
                raw = source.encode("utf-8")
                sha = M._git_blob_sha1(raw)
                if self.contents_sha_override:
                    sha = self.contents_sha_override
                return 200, {"type": "file", "path": policy_path,
                             "encoding": "base64", "size": len(raw),
                             "sha": sha, "download_url": "https://ignored",
                             "content": base64.b64encode(raw).decode("ascii")}
        if path.startswith(f"/repos/{_PRODUCTION_REPO}/pulls/4100/files?"):
            page = int(path.rsplit("page=", 1)[1])
            return 200, self.files_pages[page - 1] if page <= len(self.files_pages) else []
        if path == f"/repos/{_PRODUCTION_REPO}/pulls/4100":
            return 200, self.final_pull
        if path.startswith(f"/repos/{_PRODUCTION_REPO}/pulls/4100/commits?"):
            page = int(path.rsplit("page=", 1)[1])
            if self.commits_pages is None:
                return 404, {"message": "Not Found"}
            return 200, (self.commits_pages[page - 1]
                         if page <= len(self.commits_pages) else [])
        if path.startswith(f"/repos/{_PRODUCTION_REPO}/rules/branches/master?"):
            page = int(path.rsplit("page=", 1)[1])
            return 200, (self.rules_pages[page - 1]
                         if page <= len(self.rules_pages) else [])
        if path == f"/repos/{_PRODUCTION_REPO}/branches/master/protection":
            return self.protection_status, self.protection_body
        return 500, {"message": "unexpected route", "route": path}


def make_pull(**over):
    pull = {"number": 4100, "state": "open", "draft": False,
            "user": {"login": "authorone"},
            "head": {"ref": "feature/x", "sha": _HEAD,
                     "repo": {"full_name": _PRODUCTION_REPO}},
            "base": {"ref": "main", "sha": _BASE,
                     "repo": {"full_name": _PRODUCTION_REPO}},
            "additions": 1, "deletions": 0, "changed_files": 1, "commits": 1}
    pull.update(over)
    return pull


def fast_files():
    return [[{"filename": "docs/evidence/report.md", "status": "modified",
              "additions": 1, "deletions": 0, "patch": "@@ -1 +1 @@"}]]


def standard_files():
    return [[{"filename": "engine/signals.py", "status": "modified",
              "additions": 5, "deletions": 2, "patch": "@@ -2 +2 @@"}]]


def critical_files():
    return [[{"filename": "tests/test_ci_native_review_policy.py",
              "status": "modified", "additions": 3, "deletions": 1,
              "patch": "@@ -3 +3 @@"}]]


def review(row_id=1, login="reviewerA", state="APPROVED",
           at="2026-11-01T00:00:00Z", utype="User"):
    row = {"id": row_id, "commit_id": _HEAD, "state": state, "submitted_at": at,
           "user": {"login": login, "type": utype},
           "pull_request_url": f"https://api.github.com/repos/{_PRODUCTION_REPO}/pulls/4100"}
    return row


def commits_pages(logins=("devone",), coauthor_lines=(), emails=None):
    rows = []
    for index, login in enumerate(logins):
        email = (emails[index] if emails else f"{login}@example.com")
        message = f"change {index}"
        for line in coauthor_lines:
            message += f"\n{line}"
        rows.append({"sha": format(0xC0 + index, "040x"),
                     "commit": {"message": message,
                                "author": {"email": email},
                                "committer": {"email": email}},
                     "author": {"login": login},
                     "committer": {"login": login}})
    return [rows]


def required_reviews_rule(count=1, code_owner=False, last_push=False,
                          dismiss=False, enforcement="active"):
    return {"type": "required_reviews", "enforcement": enforcement,
            "parameters": {"required_approving_review_count": count,
                           "require_code_owner_review": code_owner,
                           "require_last_push_approval": last_push,
                           "dismiss_stale_reviews_on_push": dismiss,
                           "allowed_merge_methods": ["merge"]}}


def qualified(result):
    assert result["disposition"] == "QUALIFIED"
    for name in ("repository", "pull_number", "head_sha", "target_ref",
                 "origin", "policy_schema", "risk_tier",
                 "minimum_independent_assessments",
                 "minimum_formal_non_author_approvals",
                 "required_independent_assessments",
                 "required_formal_non_author_approvals",
                 "accepted_independent_assessments",
                 "accepted_formal_non_author_approvals",
                 "native_review_decision_required",
                 "qualifying_reviewer_logins", "source_contributors",
                 "policy_source_identity"):
        assert name in result, name
    assert result["origin"] == "AUTOMATIC_POLICY"
    return result


def run(ref=_BASELINE_REF, *, files=None, pull=None, reviews=(), rules_pages=None,
        issuer="ciissuer", **shim):
    files = fast_files() if files is None else files
    pull = make_pull() if pull is None else pull
    shim.setdefault("files_pages", files)
    shim.setdefault("final_pull", pull)
    shim.setdefault("rules_pages", rules_pages if rules_pages is not None else [[]])
    facts = shim.pop("native_facts", native_facts())
    get = FakeGitHub(ref, **shim)
    result = M.qualify_native_review(_PRODUCTION_REPO, pull, list(reviews),
                                     issuer, get=get, now=_NOW, native_facts=facts)
    return result, get


def refused(ref=_BASELINE_REF, *, files=None, pull=None, reviews=(),
            rules_pages=None, issuer="ciissuer", **shim):
    try:
        run(ref=ref, files=files, pull=pull, reviews=reviews,
            rules_pages=rules_pages, issuer=issuer, **shim)
    except M.NativeReviewPolicyError as exc:
        return exc
    raise FixtureError("expected fail-closed NativeReviewPolicyError")


def _exec_canonical_in_parent(ref):
    """Exec the exact embedded sources under dotted control_plane names."""
    import types
    package = types.ModuleType("control_plane")
    package.__path__ = []
    registered = []
    try:
        sys.modules["control_plane"] = package
        registered.append("control_plane")
        for policy_path, source in _fixture_sources(ref).items():
            name = ("control_plane."
                    + policy_path.rsplit("/", 1)[-1][:-3])
            module = types.ModuleType(name)
            module.__file__ = policy_path
            sys.modules[name] = module
            registered.append(name)
            exec(compile(source, policy_path, "exec"), module.__dict__)
        yield sys.modules
    finally:
        for name in registered:
            sys.modules.pop(name, None)


class CanonicalSourceFixtureTests(unittest.TestCase):
    """The embedded canonical bytes are exact and complete for both pins."""

    def test_both_source_bundles_embedded_and_digest_exact(self):
        baseline = _fixture_sources(_BASELINE_REF)
        prospective = _fixture_sources(_PROSPECTIVE_REF)
        self.assertEqual(set(baseline), set(M.CANONICAL_POLICY_PATHS))
        self.assertEqual(
            baseline["control_plane/github_review_risk_source.py"],
            prospective["control_plane/github_review_risk_source.py"])

    def test_baseline_counts_are_f0_s11_c21(self):
        for modules in _exec_canonical_in_parent(_BASELINE_REF):
            policy = modules["control_plane.github_review_risk_policy"]
            dispatch = modules["control_plane.github_review_risk_dispatch"]
            self.assertEqual(dispatch.ReviewOrigin.AUTOMATIC_POLICY.value,
                             "AUTOMATIC_POLICY")
            # Requirements read off an actual assessment of a standard diff.
            facts = policy.ReviewChangeFacts(
                repository="o/r", pull_number=1, head_sha=_HEAD,
                changed_paths=("engine/signals.py",), additions=5, deletions=2,
                complete_source_verified=True, file_metrics=(
                    policy.ReviewFileStat(path="engine/signals.py",
                                          additions=5, deletions=2),))
            assessment = policy.assess_review_risk(facts)
            self.assertEqual(assessment.tier, policy.ReviewTier.STANDARD)
            self.assertEqual(
                (assessment.minimum_independent_assessments,
                 assessment.minimum_formal_non_author_approvals),
                (1, 1))
            critical = policy.assess_review_risk(
                policy.ReviewChangeFacts(
                    repository="o/r", pull_number=1, head_sha=_HEAD,
                    changed_paths=("tests/test_ci_native_review_policy.py",),
                    additions=3, deletions=1, complete_source_verified=True,
                    file_metrics=(policy.ReviewFileStat(
                        path="tests/test_ci_native_review_policy.py",
                        additions=3, deletions=1),)))
            self.assertEqual(critical.tier, policy.ReviewTier.CRITICAL)
            self.assertEqual(
                (critical.minimum_independent_assessments,
                 critical.minimum_formal_non_author_approvals),
                (2, 1))

    def test_prospective_counts_are_f0_s00_c10(self):
        for modules in _exec_canonical_in_parent(_PROSPECTIVE_REF):
            policy = modules["control_plane.github_review_risk_policy"]
            self.assertEqual(policy.minimum_review_requirements(policy.ReviewTier.STANDARD), (0, 0))
            self.assertEqual(policy.minimum_review_requirements(policy.ReviewTier.CRITICAL), (1, 0))


class QualificationFlowTests(unittest.TestCase):

    def test_fast_baseline_zero_requirements_skips_reviews_and_genealogy(self):
        result, shim = run()
        qualified(result)
        self.assertEqual(result["risk_tier"], "FAST")
        self.assertEqual(result["required_independent_assessments"], 0)
        self.assertEqual(result["required_formal_non_author_approvals"], 0)
        self.assertEqual(result["accepted_independent_assessments"], 0)
        self.assertFalse(result["native_review_decision_required"])
        self.assertFalse(any("/commits?" in call for call in shim.calls))
        self.assertEqual(result["technical_channel"], "NONE_REQUIRED")

    def test_prospective_standard_new_profile_passes_without_reviews(self):
        result, _ = run(ref=_PROSPECTIVE_REF, files=standard_files(),
                        pull=make_pull(additions=5, deletions=2))
        qualified(result)
        self.assertEqual(result["risk_tier"], "STANDARD")
        self.assertEqual(result["minimum_independent_assessments"], 0)
        self.assertEqual(result["minimum_formal_non_author_approvals"], 0)

    def test_authenticated_normal_email_identity_accepted_when_owed(self):
        result, shim = run(files=standard_files(),
                           pull=make_pull(additions=5, deletions=2),
                           reviews=[review()],
                           commits_pages=commits_pages())
        qualified(result)
        self.assertEqual(result["required_independent_assessments"], 1)
        self.assertEqual(result["accepted_independent_assessments"], 1)
        self.assertEqual(result["accepted_formal_non_author_approvals"], 1)
        self.assertEqual(result["qualifying_reviewer_logins"], ["reviewerA"])
        self.assertIn("devone", result["source_contributors"])
        self.assertTrue(any("/commits?" in call for call in shim.calls))

    def test_reviewer_equal_to_issuer_counts_two_seats(self):
        result, _ = run(files=standard_files(),
                        pull=make_pull(additions=5, deletions=2),
                        reviews=[review(login="ciissuer")],
                        commits_pages=commits_pages())
        qualified(result)
        self.assertEqual(result["qualifying_reviewer_logins"], ["ciissuer"])
        self.assertEqual(result["issuer_login"], "ciissuer")

    def test_baseline_standard_requires_one_each(self):
        exc = refused(files=standard_files(),
                      pull=make_pull(additions=5, deletions=2),
                      reviews=[])
        self.assertEqual(exc.reason, "APPROVAL_CHANNEL_UNAVAILABLE")
        self.assertEqual(exc.details["required_independent_assessments"], 1)
        self.assertEqual(exc.details["required_formal_non_author_approvals"], 1)
        self.assertEqual(exc.details["accepted_independent_assessments"], 0)

    def test_baseline_critical_respects_two_and_one(self):
        pull = make_pull(additions=3, deletions=1)
        two = [review(row_id=1, login="revA"), review(row_id=2, login="revB")]
        result, _ = run(files=critical_files(), pull=pull, reviews=two,
                        commits_pages=commits_pages())
        qualified(result)
        self.assertEqual(result["risk_tier"], "CRITICAL")
        self.assertEqual(result["required_independent_assessments"], 2)
        self.assertEqual(result["required_formal_non_author_approvals"], 1)
        self.assertEqual(result["accepted_independent_assessments"], 2)
        one = [review(row_id=1, login="revA")]
        exc = refused(files=critical_files(), pull=pull, reviews=one,
                      commits_pages=commits_pages())
        self.assertEqual(exc.reason, "REVIEW_REQUIREMENTS_UNMET")
        self.assertEqual(exc.details["accepted_independent_assessments"], 1)

    def test_prospective_critical_technical_hold_keeps_formal_zero(self):
        exc = refused(ref=_PROSPECTIVE_REF, files=critical_files(),
                      pull=make_pull(additions=3, deletions=1),
                      reviews=[review(login="authorone")],
                      commits_pages=commits_pages(logins=("authorone",)))
        self.assertIsInstance(exc, M.TechnicalProvenanceUnavailable)
        self.assertEqual(exc.code, "TECHNICAL_PROVENANCE_UNAVAILABLE")
        self.assertEqual(exc.details["required_independent_assessments"], 1)
        self.assertEqual(exc.details["required_formal_non_author_approvals"], 0)

    def test_advisory_and_pass_states_never_satisfy_channels(self):
        exc = refused(files=standard_files(),
                      pull=make_pull(additions=5, deletions=2),
                      reviews=[review(state="COMMENTED")])
        self.assertEqual(exc.reason, "APPROVAL_CHANNEL_UNAVAILABLE")
        exc = refused(files=standard_files(),
                      pull=make_pull(additions=5, deletions=2),
                      reviews=[review(state="PASS")])
        self.assertEqual(exc.reason, "REVIEW_ROW_MALFORMED")




    def test_changes_requested_and_dismissed_stay_binding(self):
        for later in ("CHANGES_REQUESTED", "DISMISSED"):
            reviews = [review(row_id=1, login="revA"),
                       review(row_id=2, login="revA", state=later,
                              at="2026-11-02T00:00:00Z")]
            exc = refused(files=standard_files(),
                          pull=make_pull(additions=5, deletions=2),
                          reviews=reviews)
            self.assertEqual(exc.reason, "CURRENT_REVIEW_REQUESTS_CHANGES" if later=="CHANGES_REQUESTED" else "APPROVAL_CHANNEL_UNAVAILABLE", later)

    def test_commented_and_pending_do_not_erase_approval(self):
        for later, at in (("COMMENTED", "2026-11-02T00:00:00Z"),
                          ("PENDING", None)):
            reviews = [review(row_id=1, login="revA"),
                       review(row_id=2, login="revA", state=later, at=at)]
            result, _ = run(files=standard_files(),
                            pull=make_pull(additions=5, deletions=2),
                            reviews=reviews, commits_pages=commits_pages())
            qualified(result)
            self.assertEqual(result["qualifying_reviewer_logins"], ["revA"])

    def test_source_author_self_review_refused(self):
        exc = refused(files=standard_files(),
                      pull=make_pull(additions=5, deletions=2),
                      reviews=[review(login="authorone")],
                      commits_pages=commits_pages())
        self.assertIn(exc.reason, ("APPROVAL_CHANNEL_UNAVAILABLE",
                                   "REVIEW_REQUIREMENTS_UNMET"))

    def test_commit_author_login_is_contributor_even_with_foreign_review(self):
        exc = refused(files=standard_files(),
                      pull=make_pull(additions=5, deletions=2),
                      reviews=[review(login="devone")],
                      commits_pages=commits_pages())
        self.assertEqual(exc.reason, "REVIEW_REQUIREMENTS_UNMET")
        self.assertEqual(exc.details["accepted_independent_assessments"], 0)

    def test_unmapped_coauthor_is_scoped_independence_gap(self):
        exc = refused(files=standard_files(),
                      pull=make_pull(additions=5, deletions=2),
                      reviews=[review()],
                      commits_pages=commits_pages(
                          coauthor_lines=["Co-authored-by: Co Dev <ghost@example.com>"]))
        self.assertEqual(exc.reason, "INDEPENDENCE_UNVERIFIABLE_CONTRIBUTOR_IDENTITY")
        self.assertEqual(exc.details["unmapped"], ["coauthor"])

    def test_noreply_coauthor_resolved_without_normal_email_requirement(self):
        result, _ = run(files=standard_files(),
                        pull=make_pull(additions=5, deletions=2),
                        reviews=[review()],
                        commits_pages=commits_pages(
                            coauthor_lines=["Co-authored-by: Co Dev <92740115+codev@users.noreply.github.com>"]))
        qualified(result)
        self.assertIn("codev", result["source_contributors"])
        self.assertEqual(result["qualifying_reviewer_logins"], ["reviewerA"])


class MalformedAndHostileInputTests(unittest.TestCase):

    def test_duplicate_review_row_fails_closed(self):
        exc = refused(files=standard_files(),
                      pull=make_pull(additions=5, deletions=2),
                      reviews=[review(row_id=1), review(row_id=1)])
        self.assertEqual(exc.reason, "REVIEW_ROW_DUPLICATE")

    def test_malformed_rows_fail_closed(self):
        cases = [
            [review(row_id=True)],
            [review(login="")],
            [{"id": 1, "state": "APPROVED", "submitted_at": "2026-11-01T00:00:00Z",
              "user": "reviewerA"}],
            [review(at="not-a-timestamp")],
            [{"id": 1, "state": "APPROVED", "submitted_at": None,
              "user": {"login": "revA", "type": "User"}}],
        ]
        for reviews in cases:
            exc = refused(files=standard_files(),
                          pull=make_pull(additions=5, deletions=2),
                          reviews=reviews)
            self.assertEqual(exc.reason, "REVIEW_ROW_MALFORMED", reviews)



    def test_wrong_repository_and_fork_and_draft_refused(self):
        get = FakeGitHub(_BASELINE_REF, files_pages=fast_files(),
                         final_pull=make_pull(), rules_pages=[[]])
        try:
            M.qualify_native_review("other/repo", make_pull(), [], None,
                                    get=get, now=_NOW)
        except M.NativeReviewPolicyError as exc:
            self.assertEqual(exc.reason, "PRODUCTION_REPOSITORY_MISMATCH")
        else:
            raise FixtureError("wrong repository accepted")
        exc = refused(pull=make_pull(head={"ref": "feature/x", "sha": _HEAD,
                                           "repo": {"full_name": "forkorg/macro"}}))
        self.assertEqual(exc.reason, "PR_FORK_OR_FOREIGN_REPOSITORY")
        exc = refused(final_pull=make_pull(draft=True))
        self.assertEqual(exc.reason, "POLICY_EVALUATION_REFUSED")
        self.assertEqual(exc.details["child_code"], "PR_NOT_REVIEWABLE")
        exc = refused(pull=make_pull(draft=True))
        self.assertEqual(exc.reason, "POLICY_EVALUATION_REFUSED")
        self.assertEqual(exc.details["child_code"], "PR_NOT_REVIEWABLE")

    def test_moved_head_between_snapshot_and_final_refused(self):
        exc = refused(final_pull=make_pull(head={"ref": "feature/x", "sha": "c" * 40,
                                                 "repo": {"full_name": _PRODUCTION_REPO}}))
        self.assertEqual(exc.reason, "POLICY_EVALUATION_REFUSED")
        self.assertIn(exc.details["child_code"],
                      ("PR_SOURCE_MOVED_DURING_CENSUS", "PR_SOURCE_HEAD_MOVED"))

    def test_incomplete_files_refused(self):
        exc = refused(files=fast_files(),
                      pull=make_pull(changed_files=2, additions=1))
        self.assertEqual(exc.reason, "POLICY_EVALUATION_REFUSED")
        self.assertEqual(exc.details["child_code"], "PR_SOURCE_PAGINATION_INCOMPLETE")

    def test_renamed_without_previous_path_refused(self):
        files = [[{"filename": "docs/evidence/moved.md", "status": "renamed",
                   "additions": 1, "deletions": 0, "patch": "@@ -1 +1 @@"}]]
        exc = refused(files=files)
        self.assertEqual(exc.reason, "POLICY_EVALUATION_REFUSED")
        self.assertEqual(exc.details["child_code"], "PR_PREVIOUS_PATH_MISSING")

    def test_renamed_previous_path_is_sensitive_input(self):
        files = [[{"filename": "security/vault.py", "status": "renamed",
                   "previous_filename": "docs/evidence/old.md",
                   "additions": 1, "deletions": 0, "patch": "@@ -1 +1 @@"}]]
        two = [review(row_id=1, login="revA"), review(row_id=2, login="revB")]
        result, _ = run(files=files, reviews=two, commits_pages=commits_pages())
        qualified(result)
        self.assertEqual(result["risk_tier"], "CRITICAL")
        self.assertEqual(result["required_independent_assessments"], 2)
        self.assertEqual(result["accepted_independent_assessments"], 2)

    def test_missing_code_patch_refused(self):
        files = [[{"filename": "docs/evidence/report.md", "status": "modified",
                   "additions": 1, "deletions": 0}]]
        exc = refused(files=files)
        self.assertEqual(exc.reason, "POLICY_EVALUATION_REFUSED")
        self.assertEqual(exc.details["child_code"], "PR_CODE_PATCH_MISSING")

    def test_policy_source_head_movement_refused(self):
        exc = refused(branch_reads=[(200, {"name": "master", "protected": True,
                                           "commit": {"sha": _BASELINE_REF}}),
                                    (200, {"name": "master", "protected": True,
                                           "commit": {"sha": "d" * 40}})])
        self.assertEqual(exc.reason, "POLICY_SOURCE_MOVED")

    def test_unprotected_source_branch_refused(self):
        exc = refused(branch_reads=[(200, {"name": "master", "protected": False,
                                           "commit": {"sha": _BASELINE_REF}})])
        self.assertEqual(exc.reason, "POLICY_BRANCH_NOT_PROTECTED")

    def test_blob_mismatch_refused(self):
        exc = refused(contents_sha_override="0" * 40)
        self.assertEqual(exc.reason, "POLICY_MODULE_BLOB_MISMATCH")

    def test_http_403_is_preserved_on_read_error(self):
        exc = refused(overrides={"/pulls/4100/files": (403, {"message": "Forbidden"})})
        self.assertIsInstance(exc, M.NativeReviewReadError)
        self.assertEqual(exc.status_code, 403)
        self.assertEqual(exc.response_json, {"message": "Forbidden"})




    def test_malformed_read_callback_result(self):
        with self.assertRaises(M.NativeReviewPolicyError) as caught:
            M.qualify_native_review(_PRODUCTION_REPO, make_pull(), [], None,
                                    get=lambda path: (200, {}),
                                    now=_NOW)
        self.assertEqual(caught.exception.reason, "READ_CALLBACK_MALFORMED_RESULT")
        with self.assertRaises(M.NativeReviewPolicyError) as caught:
            M.qualify_native_review(_PRODUCTION_REPO, make_pull(), [], None,
                                    get=lambda path: {},
                                    now=_NOW)
        self.assertIn(caught.exception.reason,
                      ("POLICY_BRANCH_MALFORMED", "POLICY_BRANCH_HTTP_REFUSED",
                       "POLICY_BRANCH_NOT_PROTECTED",
                       "POLICY_EVALUATION_REFUSED"))


class PaginationAndIsolationTests(unittest.TestCase):


    def test_commits_pagination_bounded_by_declared_count(self):
        pull = make_pull(commits=150, additions=5, deletions=2)
        page_one = commits_pages(logins=[f"dev{n:03d}" for n in range(100)])[0]
        page_two = commits_pages(logins=[f"dev{n:03d}" for n in range(100, 150)])[0]
        for i,row in enumerate(page_two): row["sha"]=format(0x1000+i,"040x")
        result, _ = run(files=standard_files(), pull=pull,
                        reviews=[review()], commits_pages=[page_one, page_two])
        qualified(result)
        self.assertIn("dev049", result["source_contributors"])
        self.assertIn("dev120", result["source_contributors"])

    def test_commit_count_mismatch_refused(self):
        pull = make_pull(commits=3, additions=5, deletions=2)
        exc = refused(files=standard_files(), pull=pull, reviews=[review()],
                      commits_pages=commits_pages())
        self.assertEqual(exc.reason, "PR_COMMITS_INCONSISTENT")
        self.assertEqual(exc.details["declared"], 3)
        self.assertEqual(exc.details["fetched"], 1)

    def test_control_plane_namespace_poisoning_resisted(self):
        fake = types_module_poison()
        saved = sys.modules.get("control_plane")
        sys.modules["control_plane"] = fake
        try:
            result, _ = run(files=standard_files(),
                            pull=make_pull(additions=5, deletions=2),
                            reviews=[review()],
                            commits_pages=commits_pages())
            qualified(result)
            self.assertEqual(result["required_independent_assessments"], 1)
            self.assertEqual(result["accepted_independent_assessments"], 1)
        finally:
            if saved is None:
                sys.modules.pop("control_plane", None)
            else:
                sys.modules["control_plane"] = saved

    def test_child_environment_carries_no_secrets(self):
        env = M._CHILD_ENV
        self.assertEqual(set(env), {"PATH", "LC_ALL", "PYTHONHASHSEED"})
        for key, value in env.items():
            self.assertNotIn("token", key.lower())
            self.assertNotIn("ghp_", str(value))

    def test_now_variants_are_audit_only(self):
        results = []
        for now in (_NOW, 1762100000, datetime.fromtimestamp(_NOW, tz=timezone.utc),
                    (lambda: 1762100000)):
            get = FakeGitHub(_BASELINE_REF, files_pages=fast_files(),
                             final_pull=make_pull(), rules_pages=[[]])
            results.append(M.qualify_native_review(
                _PRODUCTION_REPO, make_pull(), [], None, get=get, now=now))
        for result in results:
            qualified(result)
            self.assertIn(result["now_observation"]["source"],
                          ("epoch", "datetime", "clock_callable"))

    def test_now_bool_and_naive_datetime_refused(self):
        for bad in (True, False, datetime.fromtimestamp(_NOW)):
            get = FakeGitHub(_BASELINE_REF, files_pages=fast_files(),
                             final_pull=make_pull(), rules_pages=[[]])
            with self.assertRaises(M.NativeReviewPolicyError):
                M.qualify_native_review(_PRODUCTION_REPO, make_pull(), [],
                                        None, get=get, now=bad)


def types_module_poison():
    import types

    class FakeControlPlane(types.ModuleType):
        pass

    fake = FakeControlPlane("control_plane")
    fake.__path__ = []
    fake.assess_current_pr_risk_with_final = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("poisoned namespace used"))
    return fake




class FrozenCallerAcceptanceTests(unittest.TestCase):
    def test_native_facts_are_strict_complete_current_and_qualified(self):
        changes=[{"required_formal_approvals":True}, {"requires_code_owner_reviews":1},
            {"review_decision_required":1}, {"native_enforcement_qualified":False},
            {"head_sha":"b"*40}, {"pr_number":True}, {"repository":"other/repo"},
            {"target_ref":"master"}, {"protection_source_sha":"bad"},
            {"review_decision":"UNKNOWN"}]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(M.NativeReviewPolicyError):
                    run(native_facts=native_facts(**change))
        facts=native_facts();facts.pop("review_decision_required")
        with self.assertRaises(M.NativeReviewPolicyError):run(native_facts=facts)

    def test_zero_numeric_lastpush_semantics_still_bind(self):
        for decision in (None,"REVIEW_REQUIRED","CHANGES_REQUESTED"):
            with self.assertRaises(M.NativeReviewPolicyError):
                run(native_facts=native_facts(review_decision_required=True,review_decision=decision))
        result,get=run(native_facts=native_facts(review_decision_required=True,review_decision="APPROVED"))
        self.assertTrue(result["native_review_decision_required"])
        self.assertEqual(result["required_formal_non_author_approvals"],0)
        self.assertFalse(any("/commits" in x or "/protection" in x or "/rules/" in x for x in get.calls))

    def test_maximum_counts_and_codeowner_requirement(self):
        result,get=run(files=critical_files(),pull=make_pull(additions=3,deletions=1),
            reviews=[review(1,"revA"),review(2,"revB")],commits_pages=commits_pages(),
            native_facts=native_facts(required_formal_approvals=2,requires_code_owner_reviews=True,
                review_decision_required=True,review_decision="APPROVED"))
        self.assertEqual(result["required_independent_assessments"],2)
        self.assertEqual(result["required_formal_non_author_approvals"],2)
        self.assertTrue(result["native_review_decision_required"])
        self.assertFalse(any("/protection" in x or "/rules/" in x for x in get.calls))

    def test_zero_review_needs_no_commit_count_or_mapping(self):
        pull=make_pull();pull.pop("commits")
        result,get=run(pull=pull)
        qualified(result)
        self.assertFalse(any("/commits" in x for x in get.calls))

    def test_nonformal_gap_preserves_zero_formal_minimum(self):
        exc=refused(ref=_PROSPECTIVE_REF,files=critical_files(),pull=make_pull(additions=3,deletions=1))
        self.assertEqual(exc.code,"TECHNICAL_PROVENANCE_UNAVAILABLE")
        self.assertEqual(exc.details["required_formal_non_author_approvals"],0)

    def test_stale_server_approval_cannot_supply_current_technical_review(self):
        row=review();row["commit_id"]="e"*40
        exc=refused(ref=_PROSPECTIVE_REF,files=critical_files(),pull=make_pull(additions=3,deletions=1),
            reviews=[row],commits_pages=commits_pages())
        self.assertEqual(exc.code,"TECHNICAL_PROVENANCE_UNAVAILABLE")

    def test_native_only_formal_may_reuse_server_valid_stale_approval(self):
        row=review();row["commit_id"]="e"*40
        result,_=run(reviews=[row],commits_pages=commits_pages(),
            native_facts=native_facts(required_formal_approvals=1,review_decision_required=True,review_decision="APPROVED"))
        self.assertEqual(result["accepted_independent_assessments"],0)
        self.assertEqual(result["accepted_formal_non_author_approvals"],1)

    def test_real_top_level_author_mapping_excludes_source_builder(self):
        rows=commits_pages(logins=("reviewerA",))
        self.assertNotIn("user",rows[0][0]["commit"]["author"])
        exc=refused(files=standard_files(),pull=make_pull(additions=5,deletions=2),reviews=[review()],commits_pages=rows)
        self.assertEqual(exc.reason,"REVIEW_REQUIREMENTS_UNMET")

    def test_fictional_nested_mapping_never_replaces_missing_server_mapping(self):
        rows=commits_pages();rows[0][0]["author"]=None
        rows[0][0]["commit"]["author"]["user"]={"login":"invented"}
        exc=refused(files=standard_files(),pull=make_pull(additions=5,deletions=2),reviews=[review()],commits_pages=rows)
        self.assertEqual(exc.reason,"INDEPENDENCE_UNVERIFIABLE_CONTRIBUTOR_IDENTITY")

    def test_latest_blocking_review_preserved_even_when_no_review_is_owed(self):
        exc=refused(reviews=[review(state="CHANGES_REQUESTED")])
        self.assertEqual(exc.reason,"CURRENT_REVIEW_REQUESTS_CHANGES")

    def test_real_read_error_constructor_matches_core(self):
        exc=M.NativeReviewReadError(403,{"message":"Forbidden"})
        self.assertEqual(exc.status_code,403)
        self.assertEqual(exc.response_json,{"message":"Forbidden"})
        self.assertNotIn("Forbidden",str(exc))

    def test_actual_core_invokes_real_helper_with_frozen_callback(self):
        from unittest import mock
        try:
            from scripts import merge_on_green as mog
        except ImportError:
            self.skipTest("actual core checkout required on PYTHONPATH")
        # Use the REAL supplier, not the permissive fixture default wrapper.
        with mock.patch.dict(sys.modules,{"scripts.ci_native_review_policy":M}), mock.patch.object(M,"qualify_native_review",_REAL_QUALIFY):
            for owed in (False,True):
                with self.subTest(owed=owed):
                    pull=make_pull(additions=5,deletions=2) if owed else make_pull()
                    pull.update(merged=False,title="Qualified change",body="Ordinary source",labels=[{"name":"merge-on-green"}])
                    reviews=[review(login="ciissuer")] if owed else []
                    shim=FakeGitHub(_BASELINE_REF,files_pages=standard_files() if owed else fast_files(),
                        final_pull=pull,commits_pages=commits_pages() if owed else None)
                    group=dict(pr_number=4100,source_head_sha=_HEAD,target_ref="main")
                    protection=dict(target_ref="main",protected_source_sha="a"*40,
                        required_workflows=sorted([".github/workflows/ci.yml",".github/workflows/fences.yml",".github/workflows/ci-authority.yml"]),
                        required_formal_approvals=0,requires_code_owner_reviews=False,review_decision_required=False)
                    row=dict(id="PR_4100",number=4100,state="OPEN",isDraft=False,headRefOid=_HEAD,baseRefName="main",reviewDecision=None,
                        baseRef=dict(name="main",branchProtectionRule=None))
                    def request(method,url,token,*args,**kwargs):
                        if method=="POST" and url.endswith("/graphql"):
                            return 200,dict(data=dict(repository=dict(nameWithOwner=_PRODUCTION_REPO,pullRequest=row)))
                        path=url.removeprefix(mog.GITHUB_API)
                        if path.endswith("/reviews?per_page=100&page=1"):return 200,reviews
                        if path.endswith("/events?per_page=100&page=1"):
                            return 200,[dict(id=1,event="labeled",label=dict(name="merge-on-green"),actor=dict(login="ciissuer"))]
                        if path.endswith("/permission"):return 200,dict(permission="write")
                        return shim._response(path)
                    checks=[dict(name="CI",status="completed",conclusion="success")]
                    with mock.patch.object(mog,"_request",request),mock.patch.object(mog,"fetch_issue_comments",return_value=[]),mock.patch.object(mog,"head_check_runs",return_value=checks):
                        result=mog.native_current_release(_PRODUCTION_REPO,"fixture",group,protection=protection)
                    self.assertEqual(result["node_id"],"PR_4100")
                    self.assertFalse(any("/protection" in x or "/rules/" in x for x in shim.calls))
                    self.assertEqual(any("/commits" in x for x in shim.calls),owed)


    def test_duplicate_commits_cannot_complete_contributor_inventory(self):
        rows=commits_pages()[0];rows=rows+rows
        exc=refused(files=standard_files(),pull=make_pull(additions=5,deletions=2,commits=2),reviews=[review()],commits_pages=[rows])
        self.assertEqual(exc.reason,"PR_COMMIT_IDENTITY_INCOMPLETE")

    def test_old_timestamp_current_subject_review_has_no_invented_expiry(self):
        result,_=run(files=standard_files(),pull=make_pull(additions=5,deletions=2),
            reviews=[review(at="2020-01-01T00:00:00Z")],commits_pages=commits_pages())
        self.assertEqual(result["accepted_independent_assessments"],1)

    def test_coauthor_normal_email_uses_later_actual_role_mapping(self):
        rows=commits_pages(logins=("devone","reviewerA"))[0]
        rows[0]["commit"]["message"]+="\nCo-authored-by: Reviewer <reviewerA@example.com>"
        exc=refused(files=standard_files(),pull=make_pull(additions=5,deletions=2,commits=2),reviews=[review()],commits_pages=[rows])
        self.assertEqual(exc.reason,"REVIEW_REQUIREMENTS_UNMET")

if __name__ == "__main__":
    unittest.main()
