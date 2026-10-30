jQuery(document).ready(function($) {
    $("input.elementor-field").each(function() {
        $('input[type="email"].elementor-field').on("invalid", function() {
            return this.setCustomValidity("אימייל לא תקין");
        });
        $('input[type="tel"].elementor-field').on("invalid", function() {
            return this.setCustomValidity("מספר טלפון לא תקין");
        });
        $(this).on("input", function() {
            return this.setCustomValidity("")
        });
    }), $(".wpcf7-acceptance").find("#signup-to-newsletter").prop("checked", !0), jQuery(document).ajaxComplete(function() {
        var e = jQuery(".elementor-form .elementor-message-danger");
        e && jQuery(e).text("שימי לב - אולי האימייל שכתבת לא תקין?")
    })
});