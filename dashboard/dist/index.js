(function () {
  "use strict";
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;
  const React = SDK.React;
  const h = React.createElement;
  const api = "/api/plugins/approval-link/requests/";

  function ApprovalCard() {
    const id = new URLSearchParams(window.location.search).get("request") || "";
    const [row, setRow] = React.useState(null);
    const [error, setError] = React.useState("");
    const [busy, setBusy] = React.useState(false);
    const [now, setNow] = React.useState(Date.now());
    React.useEffect(function () {
      let active = true;
      setRow(null);
      setError("");
      async function refresh() {
        if (!/^[A-Za-z0-9_-]{1,128}$/.test(id)) {
          if (active) setError("Open the approval card from its original conversation.");
          return;
        }
        try {
          const data = await SDK.fetchJSON(api + encodeURIComponent(id));
          if (active) { setRow(data); setError(""); }
        } catch (_) {
          if (active) { setRow(null); setError("This request is unavailable. Check that you are signed in to the correct workspace."); }
        }
        if (active) setNow(Date.now());
      }
      refresh();
      const timer = setInterval(refresh, 2000);
      return function () { active = false; clearInterval(timer); };
    }, [id]);

    async function decide(choice) {
      if (busy || !row || row.status !== "pending" || row.expires * 1000 <= Date.now()) return;
      setBusy(true);
      try {
        const data = await SDK.fetchJSON(api + encodeURIComponent(id) + "/decision", {
          method: "POST",
          headers: {"Content-Type": "application/json", "X-Approval-Link": "1"},
          body: JSON.stringify({digest: row.digest, choice: choice})
        });
        setRow(data); setError("");
      } catch (_) {
        setRow(null);
        setError("The decision could not be confirmed. Reopen this card to check its status before trying again.");
      } finally { setBusy(false); }
    }

    const pending = row && row.status === "pending" && row.expires * 1000 > now;
    let status = "Waiting for a decision.";
    if (row && !pending) {
      if (row.choice === "once") status = "Approval recorded for this request only. Execution results appear in the conversation.";
      else if (row.choice === "deny") status = "Request denied.";
      else status = "This request has expired or is no longer available.";
    }
    return h("main", {className: "approval-link-card"},
      h("h1", null, "Review this command"),
      error ? h("p", {role: "alert"}, error) : null,
      row ? h(React.Fragment, null,
        h("p", null, row.description),
        h("pre", {tabIndex: 0, "aria-label": "Command to review"}, row.command),
        h("p", {role: "status", "aria-live": "polite"}, status),
        h("div", {className: "approval-link-actions"},
          h("button", {type: "button", disabled: !pending || busy, onClick: function () { decide("once"); }}, "Approve once"),
          h("button", {type: "button", disabled: !pending || busy, onClick: function () { decide("deny"); }}, "Deny"))) : null);
  }
  window.__HERMES_PLUGINS__.register("approval-link", ApprovalCard);
}());
