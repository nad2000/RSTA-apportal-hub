POSTFIX
=======

/etc/postfix/main.cf
----

.. code-block:: ini

  # See /usr/share/postfix/main.cf.dist for a commented, more complete version


  # Debian specific:  Specifying a file name will cause the first
  # line of that file to be used as the name.  The Debian default
  # is /etc/mailname.
  #myorigin = /etc/mailname

  smtpd_banner = $myhostname ESMTP $mail_name (Debian/GNU)
  biff = no

  # appending .domain is the MUA's job.
  # append_dot_mydomain = no
  append_dot_mydomain = yes

  # Uncomment the next line to generate "delayed mail" warnings
  #delay_warning_time = 4h

  readme_directory = no

  # See http://www.postfix.org/COMPATIBILITY_README.html -- default to 2 on
  # fresh installs.
  compatibility_level = 2

  # TLS parameters
  # smtpd_tls_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
  # smtpd_tls_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
  smtpd_tls_cert_file=/etc/letsencrypt/live/pmspp.prodata.nz/fullchain.pem
  smtpd_tls_key_file=/etc/letsencrypt/live/pmspp.prodata.nz/privkey.pem
  smtpd_use_tls=yes
  smtp_tls_security_level = may
  smtpd_tls_session_cache_database = btree:${data_directory}/smtpd_scache
  smtp_tls_session_cache_database = btree:${data_directory}/smtp_scache

  # See /usr/share/doc/postfix/TLS_README.gz in the postfix-doc package for
  # information on enabling SSL in the smtp client.

  smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated defer_unauth_destination
  myhostname = pmspp.prodata.nz
  mydomain = prodata.nz
  alias_maps = hash:/etc/aliases
  alias_database = hash:/etc/aliases
  myorigin = $myhostname
  mydestination = $myhostname pmspp.prodata.nz mail.pmspp.prodata.nz localhost.prodata.nz localhost
  relayhost =
  mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128
  mailbox_size_limit = 0
  recipient_delimiter = +
  mailbox_command = /usr/bin/procmail
  inet_interfaces = all
  inet_protocols = all

  # Milter configuration  
  # OpenDKIM
  milter_default_action = accept
  # milter_protocol = 6
  milter_protocol = 6
  smtpd_milters = local:opendkim/opendkim.sock
  non_smtpd_milters = $smtpd_milters

/etc/aliases
----

After changing **/etc/aliases** run **newaliases**:

.. code-block:: ini

  # /etc/aliases
  mailer-daemon: postmaster
  postmaster: root
  nobody: root
  hostmaster: root
  usenet: root
  news: root
  webmaster: root
  www: root
  ftp: root
  abuse: root
  noc: root
  security: root
  admin: app
  pmspp: app



DKIM
====

/etc/opendkim.conf
----

.. code-block:: ini

  # This is a basic configuration that can easily be adapted to suit a standard
  # installation. For more advanced options, see opendkim.conf(5) and/or
  # /usr/share/doc/opendkim/examples/opendkim.conf.sample.

  # Log to syslog
  Syslog                  yes
  SyslogSuccess           yes
  LogWhy                  yes
  # Required to use local socket with MTAs that access the socket as a non-
  # privileged user (e.g. Postfix)
  UMask                   002

  # Sign for example.com with key in /etc/dkimkeys/dkim.key using
  # selector '2007' (e.g. 2007._domainkey.example.com)
  #Domain                 example.com
  #KeyFile                /etc/dkimkeys/dkim.key
  #Selector               2007

  # Socket smtp://localhost
  #
  # ##  Socket socketspec
  # ##
  # ##  Names the socket where this filter should listen for milter connections
  # ##  from the MTA.  Required.  Should be in one of these forms:
  # ##
  # ##  inet:port@address           to listen on a specific interface
  # ##  inet:port                   to listen on all interfaces
  # ##  local:/path/to/socket       to listen on a UNIX domain socket
  #
  #Socket                  inet:8892@localhost
  #Socket                 local:/var/run/opendkim/opendkim.sock
  Socket                  local:/var/spool/postfix/opendkim/opendkim.sock

  ##  PidFile filename
  ###      default (none)
  ###
  ###  Name of the file where the filter should write its pid before beginning
  ###  normal operations.
  #
  PidFile               /var/run/opendkim/opendkim.pid


  # Always oversign From (sign using actual From and a null From to prevent
  # malicious signatures header fields (From and/or others) between the signer
  # and the verifier.  From is oversigned by default in the Debian pacakge
  # because it is often the identity key used by reputation systems and thus
  # somewhat security sensitive.
  OversignHeaders         From

  ##  ResolverConfiguration filename
  ##      default (none)
  ##
  ##  Specifies a configuration file to be passed to the Unbound library that
  ##  performs DNS queries applying the DNSSEC protocol.  See the Unbound
  ##  documentation at http://unbound.net for the expected content of this file.
  ##  The results of using this and the TrustAnchorFile setting at the same
  ##  time are undefined.
  ##  In Debian, /etc/unbound/unbound.conf is shipped as part of the Suggested
  ##  unbound package

  # ResolverConfiguration     /etc/unbound/unbound.conf

  ##  TrustAnchorFile filename
  ##      default (none)
  ##
  ## Specifies a file from which trust anchor data should be read when doing
  ## DNS queries and applying the DNSSEC protocol.  See the Unbound documentation
  ## at http://unbound.net for the expected format of this file.

  TrustAnchorFile       /usr/share/dns/root.key

  ##  Userid userid
  ###      default (none)
  ###
  ###  Change to user "userid" before starting normal operation?  May include
  ###  a group ID as well, separated from the userid by a colon.
  #
  UserID                opendkim

  # Map domains in From addresses to keys used to sign messages
  KeyTable        refile:/etc/opendkim/key.table
  SigningTable        refile:/etc/opendkim/signing.table

  # Hosts to ignore when verifying signatures
  ExternalIgnoreList  /etc/opendkim/trusted.hosts
  InternalHosts       /etc/opendkim/trusted.hosts

  # Commonly-used options; the commented-out versions show the defaults.
  Canonicalization    relaxed/simple
  #Canonicalization    simple
  # Mode            sv
  Mode            s
  SubDomains      yes
  #ADSPAction     continue
  AutoRestart     yes
  AutoRestartRate     10/1h
  Background      yes
  DNSTimeout      5
  SignatureAlgorithm  rsa-sha256

/etc/opendkim/key.table
----

.. code-block:: ini

  20200811        pmspp.prodata.nz:20200811:/etc/opendkim/keys/20200811.private

/etc/opendkim/signing.table
----

.. code-block:: ini

  *@prod.prodata.nz   20200811
  *@pmspp.prodata.nz   20200811
  *@prodata.nz    20200811


PROCMAIL
====

.procmailrc
----

.. code-block:: ini

  :0Wc:
  | source $HOME/venv/bin/activate; python prod/email_receiver.py
