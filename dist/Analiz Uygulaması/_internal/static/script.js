$(document).ready(() => {
    $('#soldFilter').select2({ placeholder: "Kategori seçin", width: '100%' });
  
    $('#soldFilter').on('change', function () {
      const selected = $(this).val();
      if (!selected.length) {
        $('#filteredSoldChartArea').html('');
        return;
      }
      fetch('/filtered_sold_chart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_categories: selected })
      })
        .then(res => res.text())
        .then(html => {
          $('#filteredSoldChartArea').html(html);
        });
    });
  
    document.getElementById('categoryFilter')?.addEventListener('change', function () {
      const selectedCategory = this.value;
      const allRows = document.querySelectorAll('.table tbody tr');
      
      allRows.forEach(row => {
        // data-filter özelliğini kullanarak filtreleme yap
        const rowFilter = row.getAttribute('data-filter');
        
        if (selectedCategory === 'all' || rowFilter === selectedCategory) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  
    document.getElementById('toggleButton')?.addEventListener('click', function () {
      const hiddenRows = document.getElementById('hiddenRows');
      const showText = this.querySelector('.show-text');
      const hideText = this.querySelector('.hide-text');
  
      if (hiddenRows.style.display === 'none') {
        hiddenRows.style.display = 'table-row-group';
        showText.style.display = 'none';
        hideText.style.display = 'inline';
        this.classList.remove('btn-primary');
        this.classList.add('btn-danger');
      } else {
        hiddenRows.style.display = 'none';
        showText.style.display = 'inline';
        hideText.style.display = 'none';
        this.classList.remove('btn-danger');
        this.classList.add('btn-primary');
      }
    });
  
    document.getElementById('toggleMissingButton')?.addEventListener('click', function () {
      const hiddenMissingRows = document.getElementById('hiddenMissingRows');
      if (hiddenMissingRows.style.display === 'none') {
        hiddenMissingRows.style.display = 'block';
        this.textContent = 'Daha Az Göster';
      } else {
        hiddenMissingRows.style.display = 'none';
        this.textContent = 'Daha Fazla Göster';
      }
    });
  });
  
  function generatePDF() {
    const hiddenRows = document.getElementById('hiddenRows');
    if (hiddenRows) hiddenRows.style.display = 'table-row-group';
  
    const hiddenMissingRows = document.getElementById('hiddenMissingRows');
    if (hiddenMissingRows) hiddenMissingRows.style.display = 'block';
  
    window.print();
  
    setTimeout(() => {
      if (hiddenRows) hiddenRows.style.display = 'none';
      if (hiddenMissingRows) hiddenMissingRows.style.display = 'none';
    }, 1000);
  }
  