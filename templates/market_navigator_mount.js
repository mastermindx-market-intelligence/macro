/* Market Navigator — authenticated-host integration seam (not source/auth owner).
 * Host MUST provide exact access-controlled read(request,signal), the current
 * account+entitlement scope key, and on every account/instrument change rebind.
 * There is no default URL, auto-fetch, persistent state, watcher or alert.
 */
(function (root, factory) {
  'use strict';
  const exposed=factory(root);
  if (typeof module==='object' && module.exports) module.exports=exposed;
  else root.MastermindNavigatorMount=exposed;
}(typeof globalThis!=='undefined'?globalThis:this, function(root) {
  'use strict';
  const HORIZONS=['intraday','swing','position'];
  function bindingValid(b) {
    return b && typeof b==='object' && !Array.isArray(b) &&
      typeof b.subject==='string' && b.subject.length>0 && b.subject.length<=128 &&
      HORIZONS.includes(b.horizon) && typeof b.as_of==='string' &&
      typeof b.scope_key==='string' && b.scope_key.length>0 && b.scope_key.length<=160 &&
      typeof b.read==='function' && (b.subjectLabel===undefined ||
        typeof b.subjectLabel==='string') &&
      (b.language===undefined || ['en','zh'].includes(b.language)) &&
      (b.theme===undefined || ['dark','light'].includes(b.theme));
  }
  function createSurface(mount, options) {
    if (!options || typeof options.getScope!=='function' ||
        !mount || typeof mount.replaceChildren!=='function' ||
        !root.MastermindNavigatorClient || !root.MastermindNavigatorView)
      throw new TypeError('Navigator surface requires the existing host and client/view');
    let current=null, disposed=false, binding=null;
    function scopeMatches() {
      if (disposed || !binding) return false;
      try {return options.getScope()===binding.scope_key;}
      catch(_error) {return false;}
    }
    function teardown() {
      if (!current)return;
      current.controller.dispose();
      current.view.dispose();
      current=null;
    }
    function rebind(next) {
      if (disposed) throw new Error('Navigator surface disposed');
      // Clear previous principal content before even validating a new binding.
      teardown();
      binding=null;
      if (!bindingValid(next)) throw new TypeError('incomplete authenticated host binding');
      binding={
        subject:next.subject,horizon:next.horizon,as_of:next.as_of,
        subjectLabel:next.subjectLabel,
        scope_key:next.scope_key, read:next.read,
        language:next.language||'en',theme:next.theme||'dark'
      };
      const view=root.MastermindNavigatorView.createView(mount,{
        language:binding.language,theme:binding.theme,
        subjectLabel:binding.subjectLabel
      });
      const controller=root.MastermindNavigatorClient.createController({
        render:state=>{
          // A site-account or entitlement change mid-flight must never flash
          // an old account's returned content, even if host forgot to rebind.
          view.render(scopeMatches()?state:{status:'unavailable',data:null});
        },
        read:async (request,signal)=>{
          if (!scopeMatches()) throw new Error('Navigator scope changed');
          const answer=await binding.read(request,signal);
          if (!scopeMatches()) throw new Error('Navigator scope changed');
          return answer;
        }
      });
      current={view,controller};
      if (!scopeMatches()) controller.clear();
    }
    async function activate() {
      if (disposed || !current) throw new Error('Navigator surface unavailable');
      if (!scopeMatches()) {
        current.controller.clear();
        current.view.render({status:'unavailable',data:null});
        return false;
      }
      const owner=current;
      const request={subject:binding.subject,horizon:binding.horizon,as_of:binding.as_of};
      await owner.controller.load(request);
      if (current!==owner || !scopeMatches()) {
        if (current===owner) {
          owner.controller.clear();
          owner.view.render({status:'unavailable',data:null});
        }
        return false;
      }
      // True records that a host-directed read completed; client state still
      // represents unavailable or invalid data as explicit visible states.
      return true;
    }
    function setLanguage(language) {
      if (disposed || !current) throw new Error('Navigator surface unavailable');
      current.view.setLanguage(language);
    }
    function setTheme(theme) {
      if (disposed || !current) throw new Error('Navigator surface unavailable');
      current.view.setTheme(theme);
    }
    function clear() {
      if (disposed || !current)return;
      current.controller.clear();
    }
    function dispose() {
      if (disposed)return;
      teardown();binding=null;disposed=true;
    }
    return Object.freeze({rebind,activate,setLanguage,setTheme,clear,dispose});
  }
  return Object.freeze({createSurface});
}));
