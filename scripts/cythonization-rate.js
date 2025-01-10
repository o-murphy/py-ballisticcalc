/*
*  Use this script in browser developer console to calculate percentage of source cythonization
*
*/

(function() {
    let totalLines = 0;
    let pythonOverheadLines = 0;
    let totalScore = 0;  // Variable to hold the sum of scores

    // Select all non-empty lines
    document.querySelectorAll("pre.cython.line").forEach(pre => {
        // Extract text content inside the line
        let lineText = pre.textContent.trim();

        // Skip empty lines or lines that start with a comment
        if (
            lineText.match(/^\d+: #/)
            || lineText.match(/^\d+: """/)
            || !lineText.match(/:\s*\S/)
        ) return;

        totalLines++;

        // Extract the score (e.g., "score-62" means 62% Python interaction)
        let scoreMatch = pre.className.match(/score-(\d+)/);
        let score = scoreMatch ? parseInt(scoreMatch[1]) : 0;

        // Add score to totalScore
        totalScore += score;

        // Any nonzero score means it has Python overhead
        if (score > 0) {
            pythonOverheadLines++;
        }
    });

    let cythonizedLinesPercent = ((1 - pythonOverheadLines / totalLines) * 100);
    let cythonizedPercent = ((1 - totalScore / (totalLines*100)) * 100).toFixed(2);
    console.log(`# Total Score: ${totalScore}, Possible Score: ${totalLines*100}`)
    console.log(`# Total Non-Empty Lines: ${totalLines}`);
    console.log(`# Python Overhead Lines: ${pythonOverheadLines}`);
    console.log(`# Cythonization Percentage: ${cythonizedPercent}%`);
    console.log(`# Python Overhead Lines Percentage: ${(100-cythonizedLinesPercent).toFixed(2)}%`);
    // console.log(`Total Score Sum: ${totalScore}`);  // Output the sum of all scores
    // console.log(`Total Score Rate: ${1 - (totalScore / totalLines*100) * 100}`);  // Output the sum of all scores
})();

// (function() {
//     let totalLines = 0;
//     let pythonOverheadLines = 0;
//
//     // Select all `<pre>` elements with the "cython line" class
//     document.querySelectorAll("pre.cython.line").forEach(pre => {
//         totalLines++;
//
//         // Extract the score (e.g., "score-62" => 62)
//         let scoreMatch = pre.className.match(/score-(\d+)/);
//         let score = scoreMatch ? parseInt(scoreMatch[1]) : 0;
//
//         // Any nonzero score means it has Python overhead
//         if (score > 0) {
//             pythonOverheadLines++;
//         }
//     });
//
//     let cythonizedPercent = ((1 - pythonOverheadLines / totalLines) * 100).toFixed(2);
//
//     console.log(`Total Lines: ${totalLines}`);
//     console.log(`Python Overhead Lines: ${pythonOverheadLines}`);
//     console.log(`Cythonization Percentage: ${cythonizedPercent}%`);
// })();
