% include('tbstop.tpl', page='index', page_title='OwnTracks Pista')
%if 'index' in pistapages:


<h2>Pista</h2>

<p>
This is Pista, the Web interface to the OwnTracks data. If you are viewing this
from behind an HTTP proxy, it is <i>unlikely</i> that the required Websocket
connections will work.
</p>

<ul>

%if 'map' in pistapages:
<li><a href="map">Map</a> shows real-time movement of OwnTracks-powered vehicles on a map.</li>
%end
%if 'table' in pistapages:
<li><a href="table">Table</a> provides a tabular view to the data and is updated in real-time.</li>
%end
%if 'tracks' in pistapages:
<li><a href="tracks">Tracks</a> provides historic track data. Select the vehicle you're interested in seeing, select a date or range of dates and show on map or download the data as CSV or text.</li>
%end
%if 'console' in pistapages:
<li><a href="console">Console</a> displays the MQTT messages as they arrive.</li>
%end
%if 'status' in pistapages:
<li><a href="status">Status</a> provides an overview of connected vehicles; hover over them to see up-to-date information which is displayed in real-time.</li>
%end
%if 'jobs' in pistapages:
<li><a href="jobs">Jobs</a> provides historic job data. Select the vehicle you're interested in seeing, select a date or range of dates and show the job history or download the data as CSV or text.</li>
%end
%if 'job-edit' in pistapages:
<li><a href="job-edit">Job Edit</a> edit job details.</li>
%end
%if 'hw' in pistapages:
<li><a href="hw">Hardware</a> displays information of the individual Greenwich devices.</li>
%end

</ul>
You'll be prompted for credentials as soon as you select one of the options.


%if isdemo is True:
	<p>You are now on a demonstration site: the username is <tt>demo</tt> and the password is <tt>demo</tt>. Please note that historic data for <i>Tracks</i> is limited to a 24-hour period and is cleared out at 23:00 UTC daily.</p>
%end

<p>
Visit us at <a href="http://owntracks.de">owntracks.de</a> for more information.
</p>


%end
% include('tbsbot.tpl')
