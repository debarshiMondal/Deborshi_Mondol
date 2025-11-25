<mxfile host="app.diagrams.net" agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36" version="29.1.0">
  <diagram id="ENV_SYNC_UI" name="ENV_SYNC UI Flow">
    <mxGraphModel dx="751" dy="2463" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1920" pageHeight="2000" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="user" parent="1" style="ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;" value="User&#xa;(Browser UI)" vertex="1">
          <mxGeometry height="70" width="140" x="60" y="40" as="geometry" />
        </mxCell>
        <mxCell id="login" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" value="/login&#xa;Login Page&#xa;- Username + Password form&#xa;- Error message on invalid login" vertex="1">
          <mxGeometry height="110" width="220" x="260" y="30" as="geometry" />
        </mxCell>
        <mxCell id="_UU64MiXF5lXDIjEUNJX-1" edge="1" parent="1" source="dash" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;" target="login" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="dash" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" value="/dashboard&#xa;Home / Summary Page&#xa;- Shows latest Master Sync summary&#xa;- Shows latest Branch Sync summary&#xa;- Shows alerts / failures&#xa;- Quick links to modules" vertex="1">
          <mxGeometry height="130" width="220" x="640" y="30" as="geometry" />
        </mxCell>
        <mxCell id="e_user_login" edge="1" parent="1" source="user" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" target="login" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e_login_dash" edge="1" parent="1" source="login" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;labelBackgroundColor=#ffffff;entryX=0;entryY=0.75;entryDx=0;entryDy=0;" target="dash" value="On success">
          <mxGeometry relative="1" as="geometry">
            <mxPoint x="480" y="93" as="sourcePoint" />
            <mxPoint x="540" y="103" as="targetPoint" />
          </mxGeometry>
        </mxCell>
        <mxCell id="ms_page" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" value="/master-sync&#xa;Master Sync Page" vertex="1">
          <mxGeometry height="60" width="130" x="120" y="220" as="geometry" />
        </mxCell>
        <mxCell id="bs_page" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" value="/branch-sync&#xa;Branch Sync Page" vertex="1">
          <mxGeometry height="60" width="120" x="580" y="220" as="geometry" />
        </mxCell>
        <mxCell id="bsh_page" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;" value="/branch_sync_runs&#xa;Branch Sync History Page" vertex="1">
          <mxGeometry height="60" width="146" x="734" y="220" as="geometry" />
        </mxCell>
        <mxCell id="e_dash_ms" edge="1" parent="1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;labelBackgroundColor=#ffffff;" value="Click Master Sync">
          <mxGeometry relative="1" as="geometry">
            <mxPoint x="560" y="130" as="sourcePoint" />
            <mxPoint x="230" y="250" as="targetPoint" />
          </mxGeometry>
        </mxCell>
        <mxCell id="e_dash_bs" edge="1" parent="1" source="dash" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;labelBackgroundColor=#ffffff;" target="bs_page" value="Click Branch Sync">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e_dash_bsh" edge="1" parent="1" source="dash" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;labelBackgroundColor=#ffffff;" target="bsh_page" value="Click Branch History">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="dash_out" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" value="What /dashboard shows&#xa;- Latest Master Sync card&#xa;  • Status (Success / Failed)&#xa;  • Timestamp&#xa;  • Duration&#xa;  • API version&#xa;- Latest Branch Sync card&#xa;  • Per-branch status summary&#xa;- Alerts Area&#xa;  • Recent failures from Master / Branch&#xa;- Shortcut buttons / links&#xa;  • Open Master Sync page&#xa;  • Open Branch Sync page&#xa;  • Open Branch History" vertex="1">
          <mxGeometry height="240" width="290" x="920" y="-10" as="geometry" />
        </mxCell>
        <mxCell id="ms_controls" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" value="Master Sync Controls&#xa;- Button: Generate Master Sync Report&#xa;- Button: Schedule Master Sync Report" vertex="1">
          <mxGeometry height="80" width="220" x="120" y="310" as="geometry" />
        </mxCell>
        <mxCell id="e_ms_controls" edge="1" parent="1" source="ms_page" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" target="ms_controls" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="ms_latest" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" value="Latest Master Sync Summary Cards&#xa;- Duration (Previous run → Current run)&#xa;- API Version (from latest Prod dump)&#xa;- Files in Prod missing in Master&#xa;- Files in Master missing in Prod&#xa;- Common content different files&#xa;- Combined changed + missing (with author &amp; date)&#xa;- Code Comparison Report link&#xa;- Master Dump link (previous run)&#xa;- Production Dump link (current run)&#xa;- CSV download buttons for each list" vertex="1">
          <mxGeometry height="220" width="310" x="190" y="410" as="geometry" />
        </mxCell>
        <mxCell id="e_ms_latest" edge="1" parent="1" source="ms_controls" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" target="ms_latest" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="ms_history" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" value="Master Sync History Table&#xa;- Columns:&#xa;  • Timestamp&#xa;  • Status (Success / Failure reason)&#xa;  • Prod dump name&#xa;  • Key counts (missing, changed)&#xa;  • Links (CSV, code report, run folder)&#xa;- Shows last N runs&#xa;- Click row → open run folder or details" vertex="1">
          <mxGeometry height="200" width="240" x="260" y="677" as="geometry" />
        </mxCell>
        <mxCell id="e_ms_history" edge="1" parent="1" source="ms_latest" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" target="ms_history" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="ms_alerts" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" value="Master Sync Alerts Area&#xa;- If last run failed:&#xa;  • Clear failure banner&#xa;  • Short reason (e.g. Dump error, Folder validation error)&#xa;  • Link: View details / logs&#xa;- This alert is also summarized on /dashboard" vertex="1">
          <mxGeometry height="150" width="320" x="166" y="956" as="geometry" />
        </mxCell>
        <mxCell id="e_ms_alerts" edge="1" parent="1" source="ms_history" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" target="ms_alerts" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="bs_branches" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" value="Branch Sync Input Area&#xa;- Header: Logo | Title | Logout&#xa;- Live Branch List (from ~/.bashrc)&#xa;  • Example:&#xa;    2025-q4nov-release&#xa;    2025-COS3.0_Dev-release&#xa;    2026-lightningphase2-release&#xa;  • Each item links to GitHub:&#xa;    https://github.cadence.com/IT/SFDC/tree/{branch}&#xa;- Controls:&#xa;  • Radio: Single branch / All branches&#xa;  • Dropdown: choose branch (if single)&#xa;  • Button: Start Branch Sync" vertex="1">
          <mxGeometry height="210" width="330" x="510" y="310" as="geometry" />
        </mxCell>
        <mxCell id="e_bs_branches" edge="1" parent="1" source="bs_page" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" target="bs_branches" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="bs_reports" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" value="Branch Sync Output Cards&#xa;(per triggered run)&#xa;- If one branch selected:&#xa;  • Single card for that branch&#xa;- If All branches selected:&#xa;  • Separate card for each live branch&#xa;- Each branch card shows:&#xa;  • Branch name&#xa;  • Duration&#xa;  • Files in Master missing in Branch&#xa;  • Files in Branch missing in Master&#xa;  • Common content differences&#xa;  • Combined changed + missing list&#xa;  • Author log summary (last 5 authors per file)&#xa;  • Code Comparison links (if available)&#xa;  • Links to detailed diff views" vertex="1">
          <mxGeometry height="240" width="290" x="680" y="573" as="geometry" />
        </mxCell>
        <mxCell id="e_bs_reports" edge="1" parent="1" source="bs_branches" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" target="bs_reports" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="bs_deepdiff" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" value="Branch-Specific Detail Views&#xa;- Label Differences View&#xa;  • Highlight only different / missing labels&#xa;  • Red highlight for missing names&#xa;- CustomSettings Differences View&#xa;  • Table by NAME&#xa;  • Show only rows where VALUE differs&#xa;  • Red highlight for missing NAME in either side&#xa;- File-level lists and CSV download buttons&#xa;- Optional link to branch-level code compare report" vertex="1">
          <mxGeometry height="220" width="299" x="690" y="915" as="geometry" />
        </mxCell>
        <mxCell id="e_bs_deepdiff" edge="1" parent="1" source="bs_reports" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" target="bs_deepdiff" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="bsh_table" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;" value="Branch Sync History Page&lt;br&gt;/branch_sync_runs&lt;br&gt;- History Table of all branch runs&lt;br&gt;  • Timestamp&lt;br&gt;  • Branch name&lt;br&gt;  • Status (Success / Failed)&lt;br&gt;  • Summary counts (missing / changed)&lt;br&gt;  • Link to branch report/cards&lt;br&gt;- Filters:&lt;br&gt;  • By branch&lt;br&gt;  • By status&lt;br&gt;  • By date range&lt;br&gt;- Used as audit trail of all Branch Sync operations" vertex="1">
          <mxGeometry height="220" width="264" x="956" y="322" as="geometry" />
        </mxCell>
        <mxCell id="e_bsh_table" edge="1" parent="1" source="bsh_page" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" target="bsh_table" value="">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
