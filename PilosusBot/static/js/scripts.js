$(document).ready(function(){
    /**
       Set value of the alias field by removing leading and trailing
       spaces, removing non-word characters, replacing whitespaces
       with dashes, and lowering case.
    **/
    $("#title").keyup(function(){
        var titleValue = $(this).val().trim();
	titleValue = titleValue.replace(/\s+/g, '-');
	titleValue = titleValue.replace(/[^a-zA-Zа-яА-Я0-9-]+/g, '').toLowerCase();
        $("#alias").val(titleValue);
    });

    /**
       Set focus on the form, if it's body field is not empty
    **/
    function focusBody() {
	var inputField=$("#body");
	if (inputField.val()) {
	    var inputLength=inputField.val().length;
	    if (inputLength != 0) {
		inputField.focus();
		inputField[0].setSelectionRange(inputLength, inputLength);
	    }
	}
    }

    if ($("#body") != null) {
	focusBody();
    }

    /**
       Popup for action confirmation
     **/

    function confirmAlert() {
	$('.confirm').on('click', function () {
            return confirm('Are you sure?');
	});
    }

    confirmAlert();

    /**
       Fix typeahead styling for input text field for uploads search.
       Should not affect tagsinput input fields.
    **/

    $('span.twitter-typeahead').has('#image').css('display', 'block');

    /**
       Bulk select of items
     **/

    // event handler for select all checkbox
    $('#select_all').change(function() {
	var select_all = $( this );
	if ( select_all.prop('checked') ) {
	    $('.ctrl-item-select').prop('checked', $(this).prop('checked'));
	}
	else if ( select_all.not(':checked') ) {
	    $('.ctrl-item-select').removeAttr('checked');
	}
    })

    // at least one checkbox is checked
    $('input.ctrl-item-select, input#select_all').change(function() {
	if ( $('input.ctrl-item-select:checked').length > 0 ) {
	    $( '.on-check' ).show();
	}
	else {
	    $( '.on-check' ).hide();
	}
    })


});
