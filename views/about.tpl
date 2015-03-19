% include('tbstop.tpl', page='about', page_title='OwnTracks About')
%if 'about' in pistapages:

    <!-- Custom styles for this template -->
    <!-- http://vitalets.github.io/x-editable/ -->
    <link href="css/bootstrap-editable.css" rel="stylesheet">
    <script src='js/bootstrap-editable.min.js' type="text/javascript"></script>

<script type="text/javascript">

    $.fn.editable.defaults.mode = 'inline';

</script>

    <h2>About</h2>


<table id='jobtable' class="table table-bordered table-condensed">
<tr><th>number</th><th>Job</th></tr>

<tr>
	<td>1</td>
	<td><a href="#" class='jobclass' data-type="text" data-clear="1" data-pk="01">fountains</a>
		</td>
</tr>
</table>


<script type="text/javascript">

    $(document).ready(function() {
        $('#jobtable a').editable({
	    type: 'text',
	    url: function(params) {
	    		// params.name = field name
			// params.value = newly entered value
			// params.pk = 01
	                // alert(JSON.stringify(params));
			alert("Thanks for " + params.pk + " = " + params.value);
	         },
	    send: 'never',
	    title: 'Enter Job description',
	    //success: function(response, newValue) {
	    //	alert('newValue = ' + newValue);
	    //}
	});
    });
</script>


%end
% include('tbsbot.tpl')
