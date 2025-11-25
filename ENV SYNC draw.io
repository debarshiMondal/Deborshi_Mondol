<mxfile>
  <diagram id="ENV_SYNC_UI" name="ENV_SYNC UI Flow">
    <mxGraphModel dx="1600" dy="1600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1920" pageHeight="2000" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>

        <!-- USER + LOGIN + DASHBOARD -->

        <mxCell id="user" value="User&#xa;(Browser UI)" style="ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;" vertex="1" parent="1">
          <mxGeometry x="60" y="40" width="140" height="70" as="geometry"/>
        </mxCell>

        <mxCell id="login" value="/login&#xa;Login Page&#xa;- Username + Password form&#xa;- Error message on invalid login" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
          <mxGeometry x="260" y="30" width="220" height="110" as="geometry"/>
        </mxCell>

        <mxCell id="dash" value="/dashboard&#xa;Home / Summary Page&#xa;- Shows latest Master Sync summary&#xa;- Shows latest Branch Sync summary&#xa;- Shows alerts / failures&#xa;- Quick links to modules" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="1">
          <mxGeometry x="540" y="30" width="320" height="130" as="geometry"/>
        </mxCell>

        <mxCell id="e_user_login" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" edge="1" parent="1" source="user" target="login">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_login_dash" value="On success" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="login" target="dash">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- DASHBOARD: OUTGOING LINKS TO MODULES -->

        <mxCell id="ms_page" value="/master-sync&#xa;Master Sync Page" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" vertex="1" parent="1">
          <mxGeometry x="120" y="220" width="220" height="60" as="geometry"/>
        </mxCell>

        <mxCell id="bs_page" value="/branch-sync&#xa;Branch Sync Page" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1">
          <mxGeometry x="480" y="220" width="220" height="60" as="geometry"/>
        </mxCell>

        <mxCell id="bsh_page" value="/branch_sync_runs&#xa;Branch Sync History Page" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;" vertex="1" parent="1">
          <mxGeometry x="840" y="220" width="240" height="60" as="geometry"/>
        </mxCell>

        <mxCell id="e_dash_ms" value="Click Master Sync" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="dash" target="ms_page">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_dash_bs" value="Click Branch Sync" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="dash" target="bs_page">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_dash_bsh" value="Click Branch History" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;labelBackgroundColor=#ffffff;" edge="1" parent="1" source="dash" target="bsh_page">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- DASHBOARD OUTPUT DETAILS -->

        <mxCell id="dash_out" value="What /dashboard shows&#xa;- Latest Master Sync card&#xa;  • Status (Success / Failed)&#xa;  • Timestamp&#xa;  • Duration&#xa;  • API version&#xa;- Latest Branch Sync card&#xa;  • Per-branch status summary&#xa;- Alerts Area&#xa;  • Recent failures from Master / Branch&#xa;- Shortcut buttons / links&#xa;  • Open Master Sync page&#xa;  • Open Branch Sync page&#xa;  • Open Branch History" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="1">
          <mxGeometry x="920" y="40" width="380" height="200" as="geometry"/>
        </mxCell>

        <!-- MASTER SYNC PAGE: STRUCTURE AND OUTPUTS -->

        <mxCell id="ms_controls" value="Master Sync Controls&#xa;- Button: Generate Master Sync Report&#xa;- Button: Schedule Master Sync Report" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" vertex="1" parent="1">
          <mxGeometry x="80" y="310" width="260" height="80" as="geometry"/>
        </mxCell>

        <mxCell id="e_ms_controls" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" edge="1" parent="1" source="ms_page" target="ms_controls">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="ms_latest" value="Latest Master Sync Summary Cards&#xa;- Duration (Previous run → Current run)&#xa;- API Version (from latest Prod dump)&#xa;- Files in Prod missing in Master&#xa;- Files in Master missing in Prod&#xa;- Common content different files&#xa;- Combined changed + missing (with author &amp; date)&#xa;- Code Comparison Report link&#xa;- Master Dump link (previous run)&#xa;- Production Dump link (current run)&#xa;- CSV download buttons for each list" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" vertex="1" parent="1">
          <mxGeometry x="80" y="410" width="420" height="220" as="geometry"/>
        </mxCell>

        <mxCell id="e_ms_latest" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" edge="1" parent="1" source="ms_controls" target="ms_latest">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="ms_history" value="Master Sync History Table&#xa;- Columns:&#xa;  • Timestamp&#xa;  • Status (Success / Failure reason)&#xa;  • Prod dump name&#xa;  • Key counts (missing, changed)&#xa;  • Links (CSV, code report, run folder)&#xa;- Shows last N runs&#xa;- Click row → open run folder or details" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" vertex="1" parent="1">
          <mxGeometry x="80" y="650" width="420" height="200" as="geometry"/>
        </mxCell>

        <mxCell id="e_ms_history" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" edge="1" parent="1" source="ms_latest" target="ms_history">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="ms_alerts" value="Master Sync Alerts Area&#xa;- If last run failed:&#xa;  • Clear failure banner&#xa;  • Short reason (e.g. Dump error, Folder validation error)&#xa;  • Link: View details / logs&#xa;- This alert is also summarized on /dashboard" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fde9d9;strokeColor=#e46c0a;" vertex="1" parent="1">
          <mxGeometry x="80" y="870" width="420" height="150" as="geometry"/>
        </mxCell>

        <mxCell id="e_ms_alerts" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" edge="1" parent="1" source="ms_history" target="ms_alerts">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- BRANCH SYNC PAGE: STRUCTURE AND OUTPUTS -->

        <mxCell id="bs_branches" value="Branch Sync Input Area&#xa;- Header: Logo | Title | Logout&#xa;- Live Branch List (from ~/.bashrc)&#xa;  • Example:&#xa;    2025-q4nov-release&#xa;    2025-COS3.0_Dev-release&#xa;    2026-lightningphase2-release&#xa;  • Each item links to GitHub:&#xa;    https://github.cadence.com/IT/SFDC/tree/{branch}&#xa;- Controls:&#xa;  • Radio: Single branch / All branches&#xa;  • Dropdown: choose branch (if single)&#xa;  • Button: Start Branch Sync" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1">
          <mxGeometry x="480" y="310" width="420" height="210" as="geometry"/>
        </mxCell>

        <mxCell id="e_bs_branches" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" edge="1" parent="1" source="bs_page" target="bs_branches">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="bs_reports" value="Branch Sync Output Cards&#xa;(per triggered run)&#xa;- If one branch selected:&#xa;  • Single card for that branch&#xa;- If All branches selected:&#xa;  • Separate card for each live branch&#xa;- Each branch card shows:&#xa;  • Branch name&#xa;  • Duration&#xa;  • Files in Master missing in Branch&#xa;  • Files in Branch missing in Master&#xa;  • Common content differences&#xa;  • Combined changed + missing list&#xa;  • Author log summary (last 5 authors per file)&#xa;  • Code Comparison links (if available)&#xa;  • Links to detailed diff views" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1">
          <mxGeometry x="480" y="540" width="460" height="240" as="geometry"/>
        </mxCell>

        <mxCell id="e_bs_reports" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" edge="1" parent="1" source="bs_branches" target="bs_reports">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="bs_deepdiff" value="Branch-Specific Detail Views&#xa;- Label Differences View&#xa;  • Highlight only different / missing labels&#xa;  • Red highlight for missing names&#xa;- CustomSettings Differences View&#xa;  • Table by NAME&#xa;  • Show only rows where VALUE differs&#xa;  • Red highlight for missing NAME in either side&#xa;- File-level lists and CSV download buttons&#xa;- Optional link to branch-level code compare report" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1">
          <mxGeometry x="480" y="800" width="460" height="220" as="geometry"/>
        </mxCell>

        <mxCell id="e_bs_deepdiff" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" edge="1" parent="1" source="bs_reports" target="bs_deepdiff">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- BRANCH SYNC HISTORY PAGE: OUTPUTS -->

        <mxCell id="bsh_table" value="Branch Sync History Page&#xa;/branch_sync_runs&#xa;- History Table of all branch runs&#xa;  • Timestamp&#xa;  • Branch name&#xa;  • Status (Success / Failed)&#xa;  • Summary counts (missing / changed)&#xa;  • Link to branch report/cards&#xa;- Filters:&#xa;  • By branch&#xa;  • By status&#xa;  • By date range (optional)&#xa;- Used as audit trail of all Branch Sync operations" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;" vertex="1" parent="1">
          <mxGeometry x="840" y="310" width="420" height="220" as="geometry"/>
        </mxCell>

        <mxCell id="e_bsh_table" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;" edge="1" parent="1" source="bsh_page" target="bsh_table">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
