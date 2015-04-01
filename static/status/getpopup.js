
function getPopupText(data) {
        var text = "";

        var template = "\
TID     : {{tid}}\n\
IMEI    : {{imei}}\n\
Info    : {{info}}\n\
Addr    : {{addr}}\n\
Location: {{lat}}, {{lon}}\n\
Speed   : {{vel}}\n\
Altitude: {{alt}}\n\
CoG     : {{compass}}\n\
Updated : {{dstamp}}\n\
";

	if (config.activo === true) {
		template = template + "Job     : {{jobname}}\n";
	}

        try {
                text = Mustache.render(template, data);
        } catch(err) {
                text = "Cannot render Mustache";
        }
        return text;
}
