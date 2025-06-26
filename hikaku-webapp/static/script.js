/**
 * ファイル名を縮めて表示
 */
function updateFileLabel(inputId, labelId) {
  const input = document.getElementById(inputId);
  const label = document.getElementById(labelId);
  if (input && label && input.files.length > 0) {
    let name = input.files[0].name;
    if (name.length > 40) {
      name = name.substring(0, 37) + '...';
    }
    label.textContent = name;
  }
}