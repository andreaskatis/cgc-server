#include <netdb.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <linux/sockios.h>
#include <net/ethernet.h> /* the L2 protocols */
#include <linux/if.h>
#include <linux/if_arp.h>
#include <arpa/inet.h>
#define MTU 1500


static int open_raw(struct sockaddr_ll *dest_addr, char *ifname)
{
	int sock;
	struct ifreq req;
	int ret;

	sock = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
	if (sock == -1) {
		perror("Failed to open socket");
		exit(1);
	}

	bzero(&req, sizeof(req));
	strncpy(req.ifr_name, ifname, IFNAMSIZ);
	req.ifr_addr.sa_family = AF_INET;
	ret = ioctl(sock, SIOGIFINDEX, &req);
	if (ret == -1) {
		perror("Failed to get iface id");
		exit(1);
	}
	printf("%s:%d\n", ifname, req.ifr_addr.sa_family);
	bzero(dest_addr, sizeof(*dest_addr));
	dest_addr->sll_family = AF_PACKET;
	dest_addr->sll_protocol = htons(ETH_P_ALL);
	dest_addr->sll_ifindex = req.ifr_ifru.ifru_ivalue;
	dest_addr->sll_halen = ETH_ALEN;
	dest_addr->sll_hatype = ARPHRD_ETHER;
	dest_addr->sll_pkttype = PACKET_OTHERHOST;

	dest_addr->sll_addr[0] = 0xff;
	dest_addr->sll_addr[1] = 0xff;
	dest_addr->sll_addr[2] = 0xff;
	dest_addr->sll_addr[3] = 0xff;
	dest_addr->sll_addr[4] = 0xff;
	dest_addr->sll_addr[5] = 0xff;
	dest_addr->sll_addr[6] = 0xff;
	dest_addr->sll_addr[7] = 0xff;
	return sock;
}

int main()
{
	unsigned char pkt[MTU];
	uint16_t len, n;
	ssize_t nread;
	int rawsock;
	struct sockaddr_ll dest_addr;
	char iface[] = "wlan1";

	rawsock = open_raw(&dest_addr, iface);
	freopen(NULL, "rb", stdin);
	printf("Relay Started\n");
	while (1) {
		nread = fread(&len, sizeof(len), 1, stdin);
		if (nread < 0) {
			fprintf(stderr, "Failed to get length: %s", strerror(errno));
			exit(1);
		}

		len = n = ntohs(len);
		if (len == 0)
			break;

		while (len) {
			nread = fread(pkt, sizeof(char), len, stdin);
			if (nread < 0) {
				fprintf(stderr, "Failed to get length: %s", strerror(errno));
				exit(1);
			}
			len -= nread;
		}

		len = sendto(rawsock, pkt, n-1, 0, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
		if (len < 0) {
			fprintf(stderr, "Failed to send %s\n", strerror(errno));
			continue;
		}
	}

	close(rawsock);
}
