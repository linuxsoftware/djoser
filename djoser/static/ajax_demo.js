$(function() {

    function get_updates () {
        $.getJSON('/projects', function(data) {
            var target = $('#ajax-demo ul');
            target.empty();
            $.each(data, function (key, val) {
                target.append('<li>Update #' + val + '</li>');
            });
        });
    }

    $('#ajax-demo').click(function () {
        get_updates();
    });
});

