"""Original integrator's finite query repair; applies only the already delivered R1 production proposal, then reviewed corrections."""
from pathlib import Path
from hashlib import sha256
import json,subprocess
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018"); T=Path("/tmp/intl-resume-main-20261022T1252")
expected={"shared_shell_bridge.js":"31b150d8335f7abafa6210bcaf26d98a9e7e2251e34a09ce69f4524c59720e30","intl_workspace.js":"d910e296a5d6ea9b58f79ec59ab112b79a58cad21dff96f0a4831204ab06b296"}
for name,digest in expected.items():
 raw=(R/"templates"/name).read_bytes()
 assert sha256(raw).hexdigest()==digest and raw==(R/"site"/name).read_bytes()
 out=T/"query_negative_controls"/"base"/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
patch=T/"r1_production_proposal.patch"
subprocess.run(["git","apply","--check",str(patch)],cwd=R,check=True)
subprocess.run(["git","apply",str(patch)],cwd=R,check=True)
r1={"shared_shell_bridge.js":"24d7bb10d1c59a2d051b3279c436c3581ced7dfe53da3872d1452a1cde2019bf","intl_workspace.js":"f09421d4dad8dcdb86e5591d63e53836347e54afdcc2a330defa79eb672f96c5"}
for name,digest in r1.items():
 raw=(R/"templates"/name).read_bytes();assert sha256(raw).hexdigest()==digest
 out=T/"query_negative_controls"/"r1"/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
path=R/"templates/intl_workspace.js";s=path.read_text()
start=s.index("  function bindQuerySource(win) {");end=s.index("\n  function stageAndCommit(",start)
s=s[:start]+r"""  function bindQuerySource(win) {
    try {
      // Only a genuinely absent namespace without an installation marker is
      // standalone. Cleanup retains the marker; an occupied unusable namespace
      // must not silently grant the page ownership of the shell's raw query.
      if (!('MMXSharedShell' in win) && !win.__MMX_SHARED_BRIDGE_INSTALLED__) {
        return { standalone: true, shell: null, reader: null };
      }
      var shell = win.MMXSharedShell;
      if (!shell || shell.__mmxBridge !== 'mmx.shared-shell.v1') return null;
      var reader = shell.readPageSearch;
      return { standalone: false, shell: shell, reader: typeof reader === 'function' ? reader : null };
    } catch (_) { return null; }
  }

  function externalQuery(controller) {
    try {
      var source = controller.querySource;
      if (!source) return { available: false, query: null };
      var win = controller.environment.window;
      var value;
      if (source.standalone) {
        value = win.location.search;
      } else {
        if (!source.reader || win.MMXSharedShell !== source.shell ||
            source.shell.readPageSearch !== source.reader) {
          return { available: false, query: null };
        }
        value = source.reader.call(source.shell);
      }
      return typeof value === 'string' ? { available: true, query: value } : { available: false, query: null };
    } catch (_) {
      // Property access can throw as well as invocation. Keep the whole read
      // inside this boundary so live popstate can report a status-only refusal.
      return { available: false, query: null };
    }
  }
""" +s[end:]
path.write_text(s)
for name in expected:(R/"site"/name).write_bytes((R/"templates"/name).read_bytes())
nav=R/"tests/intl_country_cockpit_navigation.test.cjs";s=nav.read_text()
old="['__mmxBridge', 'active', 'applyingContext', 'navigate', 'openAuth', 'sameDocumentFragment']"
assert s.count(old)==1
s=s.replace(old,"['__mmxBridge', 'active', 'applyingContext', 'navigate', 'openAuth', 'readPageSearch', 'sameDocumentFragment']")
s=s.replace("// The helper is the only addition to the published surface.","// The additive fragment helper and query reader preserve the frozen protocol surface.")
nav.write_text(s)
print(json.dumps({"implementation":"original-integrator completion of unaccepted R1 proposal","files":[{"path":str(p.relative_to(R)),"sha256":sha256(p.read_bytes()).hexdigest()} for p in [R/"templates/shared_shell_bridge.js",R/"site/shared_shell_bridge.js",path,R/"site/intl_workspace.js",nav]],"negative_control_sources":str(T/"query_negative_controls")}))
