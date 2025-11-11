const apiKey = "AIzaSyBRkcviEqqDrERvFp9u1rO-jwaLm2QcSNE";

const input = document.getElementById("jsonInput");
const output = document.getElementById("jsonOutput");
const markdownOutput = document.getElementById("markdownOutput");
const tipsList = document.getElementById("tipsList");

document.getElementById("validateBtn").addEventListener("click", validateJSON);
document.getElementById("fixBtn").addEventListener("click", aiFixJSON);
document.getElementById("beautifyBtn").addEventListener("click", beautifyJSON);
document.getElementById("minifyBtn").addEventListener("click", minifyJSON);
document.getElementById("copyValidBtn").addEventListener("click", copyValidJSON);
document.getElementById("clearBtn").addEventListener("click", clearAll);
document.getElementById("uploadBtn").addEventListener("click", () => document.getElementById("fileInput").click());
document.getElementById("fileInput").addEventListener("change", importJSON);
document.getElementById("downloadBtn").addEventListener("click", downloadJSON);

function validateJSON() {
  try {
    const parsed = JSON.parse(input.value);
    output.textContent = JSON.stringify(parsed, null, 2);
    markdownOutput.innerHTML = "<b>✅ JSON is valid!</b>";
    tipsList.innerHTML = "<li>No issues found. JSON is perfect!</li>";
  } catch (error) {
    output.textContent = "❌ Invalid JSON.";
    markdownOutput.innerHTML = `<b>Error:</b> ${error.message}<br>Try 'AI Fix' to repair automatically.`;
    tipsList.innerHTML = "<li>Missing comma or quote?</li><li>Check braces { }</li><li>Use AI Fix for instant repair.</li>";
  }
}

async function aiFixJSON() {
  const userJSON = input.value.trim();
  if (!userJSON) return alert("Please paste JSON first!");

  output.textContent = "🤖 Thinking...";
  markdownOutput.innerHTML = "";
  tipsList.innerHTML = "";

  try {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            {
              role: "user",
              parts: [
                {
                  text: `Fix and explain this JSON.
1. Start ONLY with valid JSON formatted inside \`\`\`json ... \`\`\`.
2. Then add "### Explanation" with line-by-line tips.
Input JSON:\n${userJSON}`
                }
              ]
            }
          ]
        })
      }
    );

    const data = await res.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || "⚠️ No AI response.";
    const jsonMatch = text.match(/```json([\s\S]*?)```/);
    let fixedJsonText = jsonMatch ? jsonMatch[1].trim() : null;

    if (fixedJsonText) {
      output.textContent = fixedJsonText;
    } else {
      output.textContent = "⚠️ AI couldn’t extract valid JSON.";
    }

    const explanation = text.split(/```/).pop();
    markdownOutput.innerHTML = marked.parse(explanation || "✅ JSON fixed successfully!");

    generateTipsFromMarkdown(explanation);

  } catch (err) {
    output.textContent = "⚠️ Error: " + err.message;
  }
}

function generateTipsFromMarkdown(md) {
  const lines = md.split("\n").filter(l => l.startsWith("-") || l.startsWith("*"));
  tipsList.innerHTML = lines.length
    ? lines.map(line => `<li>${line.replace(/^[-*]\s*/, "")}</li>`).join("")
    : "<li>AI found no issues!</li>";
}

function beautifyJSON() {
  try {
    const parsed = JSON.parse(input.value);
    input.value = JSON.stringify(parsed, null, 2);
    alert("🎨 JSON formatted beautifully!");
  } catch {
    alert("Invalid JSON — use AI Fix or Validate first.");
  }
}

function minifyJSON() {
  try {
    const parsed = JSON.parse(input.value);
    input.value = JSON.stringify(parsed);
    alert("🔻 JSON minified successfully!");
  } catch {
    alert("Invalid JSON — validate first.");
  }
}

function copyValidJSON() {
  navigator.clipboard.writeText(output.textContent);
  alert("📋 Valid JSON copied!");
}

function importJSON(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    input.value = e.target.result;
  };
  reader.readAsText(file);
}

function downloadJSON() {
  const blob = new Blob([output.textContent], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "teamdev_json.json";
  a.click();
  URL.revokeObjectURL(url);
}

function clearAll() {
  input.value = "";
  output.textContent = "";
  markdownOutput.innerHTML = "";
  tipsList.innerHTML = "";
}