from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp, arp, ether_types

BRIDGE_NAME = "s1" 

class EnhancedSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(EnhancedSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.bridge_name = BRIDGE_NAME

    def add_flow(self, datapath, priority, match, actions, table_id=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority,
            match=match, instructions=inst, table_id=table_id)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info(f"Configurando o bridge: {self.bridge_name}")
        match_ip = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP)
        actions_controller = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.add_flow(datapath, 10, match_ip, actions_controller, table_id=1) 

        
        match_arp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP)
        actions_normal = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 1, match_arp, actions_normal, table_id=1)

        match_icmp = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=1) 
        actions_normal = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 1, match_icmp, actions_normal, table_id=1)

        self.logger.info("Regras de IP e ARP instaladas no switch %s", datapath.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        self.logger.info("Pacote recebido: MAC origem %s -> MAC destino %s, Porta de entrada: %s",
                         eth.src, eth.dst, in_port)
        
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            arp_pkt = pkt.get_protocol(arp.arp)
            self.logger.info("Pacote ARP: %s -> %s", arp_pkt.src_ip, arp_pkt.dst_ip)

        elif eth.ethertype == ether_types.ETH_TYPE_IP:
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            self.logger.info("Pacote IPv4: %s -> %s", ipv4_pkt.src, ipv4_pkt.dst)

            if ipv4_pkt.proto == 6:  # TCP
                tcp_pkt = pkt.get_protocol(tcp.tcp)
                self.logger.info("Pacote TCP: %s -> %s, Porta destino: %d", ipv4_pkt.src, ipv4_pkt.dst, tcp_pkt.dst_port)
            elif ipv4_pkt.proto == 17:  # UDP
                udp_pkt = pkt.get_protocol(udp.udp)
                self.logger.info("Pacote UDP: %s -> %s, Porta destino: %d", ipv4_pkt.src, ipv4_pkt.dst, udp_pkt.dst_port)

        self.mac_to_port[datapath.id] = self.mac_to_port.get(datapath.id, {})
        self.mac_to_port[datapath.id][eth.src] = in_port

        if eth.dst in self.mac_to_port[datapath.id]:
            out_port = self.mac_to_port[datapath.id][eth.dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src)
        self.add_flow(datapath, 1, match, actions, table_id=0)

        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=msg.data)
        datapath.send_msg(out)