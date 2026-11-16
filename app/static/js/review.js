// Running a review takes a while. Stop double clicks and say so.
document.getElementById('review-form')?.addEventListener('submit', (event) => {
  const form = event.currentTarget;
  setTimeout(() => {
    form.querySelector('button').disabled = true;
    document.getElementById('review-wait').hidden = false;
  }, 0);
});
