#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <assert.h>
#include <sys/time.h>
#include <time.h>
#include <fcntl.h>
#include <cdb.h>
#include <math.h>
#include "kdtree.h"	/* http://code.google.com/p/kdtree/ */
#include "mongoose.h" /* https://github.com/cesanta/mongoose */

/*
 * Copyright (C)2014 by Jan-Piet Mens <jpmens@gmail.com>
 */

#define LATLONDATAFILE "data/latlon.cdb"
#define GEONAMESDATAFILE "data/geonames.cdb"
#define HTTP_PORT "8081"

void *kd;
struct cdb cdb_geonames;
 
/*Earth Radius in Kilometers.*/
static const double R = 6372.797560856;
/*Degree vs. Radian conservation variables*/
static const double DEG_TO_RAD = M_PI/180.0;

double dist(double lat1,double lon1, double lat2, double lon2){
	double dlon = (lon2 - lon1) * DEG_TO_RAD;
	double dlat = (lat2 - lat1) * DEG_TO_RAD;
	double a =  pow(sin(dlat * 0.5),2)+ cos(lat1*DEG_TO_RAD) * cos(lat2*DEG_TO_RAD) * pow(sin(dlon * 0.5),2);
	double c = 2.0 * atan2(sqrt(a), sqrt(1-a));
	return R * c;
}
 
int find_location(float lat, float lon, char *buf, int blen)
{
	void *set;
	char *key, *val;
	unsigned klen, vlen, vpos;
	int rc = 0;
	float pos[2] = { lat, lon }, pt[2];


	set = kd_nearestf(kd, pos);
	printf("Looking for %f, %f\n", pos[0], pos[1]);

	while (!kd_res_end(set)) {
		void *data;

		kd_res_itemf(set, pt);
		printf("found location: %f, %f\n", pt[0], pt[1]);

		if ((data = kd_res_item_data(set)) != NULL) {
			printf("-> %s\n", (char *)data);
		}

		key = data;
		klen = strlen(key);

		if (cdb_find(&cdb_geonames, key, klen) > 0) {
			double d = dist(pos[0], pos[1], pt[0], pt[1]);

			vpos = cdb_datapos(&cdb_geonames);
			vlen = cdb_datalen(&cdb_geonames);
			val = malloc(vlen);
			cdb_read(&cdb_geonames, val, vlen, vpos);
			val[vlen] = '\0';

			snprintf(buf, blen, "%s|%.2lf|%s", key, d, (char *)val);
			buf[blen] = '\0';

			free(val);
			rc = 1;
			break;
		} else {
			printf("Can't find geonames key %s\n", key);
		}

		printf("%.2f %.2f\n", pos[0], pos[1]);
		kd_res_next(set);
	}
	printf("FOUND == %d\n", rc);

	kd_res_free(set);
	return (rc);
}


static int ev_handler(struct mg_connection *conn, enum mg_event ev) {
	char buf[BUFSIZ];
	float lat, lon;
	int blen = sizeof(buf);

	lat = 48.22399; /* Schramberg */
	lon = 8.38583;

	switch (ev) {
		case MG_AUTH: return MG_TRUE;
		case MG_REQUEST:
			sscanf(conn->uri + 1, "%f,%f", &lat, &lon);
			find_location(lat, lon, buf, blen);
			// mg_printf_data(conn, "%s", buf);
			mg_printf(conn, "HTTP/1.1 %d %s\r\n"
				"Content-Length: %d\r\n"
				"Content-Type: application/json; charset=UTF-8\r\n\r\n",
				200, "", strlen(buf));
			mg_write(conn, buf, strlen(buf));
			return MG_TRUE;
		default: return MG_FALSE;
	}
}

int main(int argc, char **argv)
{
	float pt[2];
	struct cdb cdb_latlon;
	int fd1, fd2;
	char *key, *val;
	unsigned klen, vlen, vpos;
	unsigned cpos;
	char *p;

	kd = kd_create(2);

	if ((fd1 = open(LATLONDATAFILE, O_RDONLY)) < 0) {
		perror(LATLONDATAFILE);
		exit(2);
	}
	if ((fd2 = open(GEONAMESDATAFILE, O_RDONLY)) < 0) {
		perror(GEONAMESDATAFILE);
		exit(2);
	}

	cdb_init(&cdb_latlon, fd1);
	cdb_init(&cdb_geonames, fd2);

	cdb_seqinit(&cpos, &cdb_latlon);
	while (cdb_seqnext(&cpos, &cdb_latlon) > 0) {

		/* cdb_read(&cdb, val, vlen, vpos); */

		klen = cdb_keylen(&cdb_latlon);
		key = malloc(klen + 1);
		cdb_read(&cdb_latlon, key, klen, cdb_keypos(&cdb_latlon));
		key[klen] = '\0';

		if (cdb_find(&cdb_latlon, key, klen) > 0) {
			vpos = cdb_datapos(&cdb_latlon);
			vlen = cdb_datalen(&cdb_latlon);
			val = malloc(vlen);
			cdb_read(&cdb_latlon, val, vlen, vpos);
			val[vlen] = '\0';
		}

		p = strchr(key, ',');
		*p = 0;

		
		pt[0] = atof(key);
		pt[1] = atof(p+1);
		assert(kd_insertf(kd, pt, val) == 0);

		free(key);
		
		/* val must not be freed; It's part of the KD node */
	}


	struct mg_server *server;

	// Create and configure the server
	server = mg_create_server(NULL, ev_handler);
	mg_set_option(server, "listening_port", HTTP_PORT);

	// Serve request. Hit Ctrl-C to terminate the program
	printf("Starting on port %s\n", mg_get_option(server, "listening_port"));
	for (;;) {
		mg_poll_server(server, 1000);
	}

	// Cleanup, and free server instance
	mg_destroy_server(&server);


	kd_free(kd);
	return 0;
}
