const { chromium } = require('playwright');
const fs = require('fs');

const URL = process.argv[2] || 'https://onlinetestpad.com/c4zopu55x4lou';
const SURNAME = process.argv[3] || 'Шурдук';
const NAME = process.argv[4] || 'Руслан';

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage();

  await page.goto(URL, { timeout: 30000, waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // Fill registration
  const visibleInputs = await page.locator('input[type=text]:visible').all();
  if (visibleInputs.length >= 2) {
    await visibleInputs[0].fill(SURNAME);
    await visibleInputs[1].fill(NAME);
  }

  // Click start
  const startBtn = page.locator('#btnNext:visible, input[type=submit][value="Далее"]:visible, input[type=submit][value="Начать"]:visible');
  await startBtn.first().click();
  await page.waitForTimeout(4000);

  // Collect all questions
  const allQuestions = [];
  let questionNum = 0;

  while (true) {
    questionNum++;

    // Get visible text (the question)
    const visibleText = await page.evaluate(() => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let text = '';
      while (walker.nextNode()) {
        const el = walker.currentNode.parentElement;
        if (el && el.offsetHeight > 0 && el.offsetWidth > 0) {
          const t = walker.currentNode.textContent.trim();
          if (t) text += t + '\n';
        }
      }
      return text;
    });

    // Get visible form elements
    const formData = await page.evaluate(() => {
      const inputs = [];
      for (const el of document.querySelectorAll('input:not([type=hidden]):not([type=submit]), textarea, select')) {
        if (el.offsetHeight === 0 || el.offsetWidth === 0) continue;

        if (el.tagName === 'SELECT') {
          const opts = [...el.options].map(o => ({ value: o.value, text: o.text }));
          inputs.push({ tag: 'select', name: el.name, id: el.id, options: opts });
        } else if (el.type === 'checkbox' || el.type === 'radio') {
          inputs.push({
            tag: el.type, name: el.name, id: el.id, value: el.value,
            label: el.parentElement?.innerText?.trim()?.substring(0, 200),
            checked: el.checked
          });
        } else {
          inputs.push({ tag: 'text', name: el.name, id: el.id, value: el.value });
        }
      }
      return inputs;
    });

    // Check if we have a "Завершить" button (last question)
    const hasFinish = await page.locator('#btnFinish:visible').count() > 0;
    const hasNext = await page.locator('#btnNext:visible').count() > 0;

    allQuestions.push({
      num: questionNum,
      text: visibleText,
      inputs: formData,
      hasNext,
      hasFinish
    });

    console.log(`Q${questionNum}: ${visibleText.substring(0, 100).replace(/\n/g, ' ')}...`);
    console.log(`  Inputs: ${formData.length} (${formData.map(i => i.tag).join(', ')})`);

    // If no "Далее" button or we hit finish, we're done collecting
    if (!hasNext && !hasFinish) break;
    if (hasFinish && !hasNext) {
      // Last question
      break;
    }

    // Click "Далее" to go to next question (WITHOUT answering - just collecting)
    if (hasNext) {
      await page.click('#btnNext');
      await page.waitForTimeout(3000);
    } else {
      break;
    }

    // Safety limit
    if (questionNum >= 30) break;
  }

  // Save all questions
  fs.writeFileSync('/tmp/testpad_all_questions.json', JSON.stringify(allQuestions, null, 2));
  console.log(`\nTotal questions collected: ${allQuestions.length}`);
  console.log('Saved to /tmp/testpad_all_questions.json');

  await browser.close();
})();
