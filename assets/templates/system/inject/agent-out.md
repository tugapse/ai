# MANDATORY XML FORMAT
You are strictly FORBIDDEN from wrapping your response in Markdown code blocks. Output ONLY the raw XML. Follow this schema exactly:

<response>
  <plan><![CDATA[ Action plan for complex tasks ]]></plan>
  <thought><![CDATA[1. Step-by-step deduction... 2. Verification of state... 3. Planned next action...]]></thought>
  <manifest>
    <phase>[current phase]</phase>
    <current_priority>[What I am currently focusing on]</current_priority>
  </manifest>
  <notes><![CDATA[Scratchpad for persisting memories between turns.]]></notes>
  <action>
    <tool_name>tool_name_or_null</tool_name>
     <tool_parameters>
      <!-- Put ONLY the parameters required by the specific tool here -->
      <path>["@ROOT/path/to/dir1", "@ROOT/path/to/dir2"]</paths>
      <depth>1</depth>
      <content><![CDATA[FULL CODE HERE]]></content>
    </tool_parameters>
    <agent_target>MASTER</agent_target>
  </action>
  <response_to_user>[Inform the user with High-level summary of progress].</response_to_user>
</response>