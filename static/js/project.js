/* Project specific Javascript goes here. */
function formset_add_a_row(btn) {
  var root = btn.form;
  // var form_idx = $('form #id_form-TOTAL_FORMS').val();
  var total = root.querySelector("#id_form-TOTAL_FORMS");
  var form_idx = total.value;

  var el = $('<tr>' + $('form #empty_form').html().replace(/__prefix__/g, form_idx) + '</tr>') ;
  setDatePickers(el);
  $('form #form_set').append(el);
  // root.querySelector("#form_set").append(el);
  //$('form #id_form-TOTAL_FORMS').val(parseInt(form_idx) + 1);
  total.value = parseInt(form_idx) + 1;
  return false;
};
