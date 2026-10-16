c-----------------------------------------------------------------------
      program p7n_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7N FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor units extracted by
c     reference/p7n_source_anchor.py:
c       stktip prb prm prfin grise prfpp   and the generated harness
c       p7n_flux (which wraps the verbatim POINTS1 flux statements).
c
c --- Local names deliberately avoid every /PUFF/, /CURRENT/, /FLAGS/ and
c     /SRCTAB/ symbol (FM, FB, X and RISE are common-block names, so a
c     scalar with one of those names would silently become an array read).
c
c --- Input on stdin, list directed:
c     line 1: mode
c     mode 1: icase hs diam fluxm vexit wsstk                     -> hdw
c     mode 2: icase vexit diam fm fb wsstk istab sqrts            -> xfinm xfinb xfin zfinm zfinb zfin
c     mode 3: icase diam vexit fm wsstk istab sqrts x xfinm zfinm -> zm
c     mode 4: icase fb wsstk x xfinb zfinb                        -> zb
c     mode 5: icase zfin fb wsstk hs hmix ta ptginv ti            -> zfin fmix hmax
c     mode 6: icase diam exitw tstak dtemp temp fmfpt1            -> fluxb fluxm
c     mode 7: icase <state 21>                                    -> htgrise risefac
c
c --- <state> is 21 values in this fixed order:
c     istype idw0 imet mrise mshear x zfinal zfrise ht0 diam0 exitw0
c     ws0 istab0 sqrts0 fm xmfin zmfin fb xbfin zbfin stipdw
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'current.puf'
      include 'puff.puf'
      include 'flags.puf'
      include 'srctab.puf'
c
      integer mode,ios,icase,istab_i
      real hs_i,diam_i,fluxm_i,vexit_i,wsstk_i,hdw_o
      real fm_i,fb_i,sqrts_i,xfinm_o,xfinb_o,xfin_o,zfinm_o,zfinb_o
      real zfin_o,dist_i,zb_o,zm_o
      real zfinp_i,hmix_i,ta_i,ptginv_i,ti_i,fmix_o,hmax_o
      real tstak_i,dtemp_i,temp_i,fmfpt1_i,fluxb_o,fluxm_o
      real st(21),htgrise_o,risefac_o
      integer i
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7N oracle: missing mode'
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,hs_i,diam_i,fluxm_i,vexit_i,wsstk_i
         if(ios.ne.0) goto 999
         call stktip(hs_i,diam_i,fluxm_i,vexit_i,wsstk_i,hdw_o)
         write(*,'(i8,1x,es20.12)') icase,hdw_o
         goto 10
      endif
c
      if(mode.eq.2)then
 20      read(*,*,iostat=ios) icase,vexit_i,diam_i,fm_i,fb_i,wsstk_i,
     &                      istab_i,sqrts_i
         if(ios.ne.0) goto 999
         call prfin(vexit_i,diam_i,fm_i,fb_i,wsstk_i,istab_i,sqrts_i,
     &              xfinm_o,xfinb_o,xfin_o,zfinm_o,zfinb_o,zfin_o)
         write(*,'(i8,6(1x,es20.12))') icase,xfinm_o,xfinb_o,xfin_o,
     &      zfinm_o,zfinb_o,zfin_o
         goto 20
      endif
c
      if(mode.eq.3)then
 30      read(*,*,iostat=ios) icase,diam_i,vexit_i,fm_i,wsstk_i,istab_i,
     &                      sqrts_i,dist_i,xfinm_o,zfinm_o
         if(ios.ne.0) goto 999
         call prm(diam_i,vexit_i,fm_i,wsstk_i,istab_i,sqrts_i,dist_i,
     &            xfinm_o,zfinm_o,zm_o)
         write(*,'(i8,1x,es20.12)') icase,zm_o
         goto 30
      endif
c
      if(mode.eq.4)then
 40      read(*,*,iostat=ios) icase,fb_i,wsstk_i,dist_i,xfinb_o,zfinb_o
         if(ios.ne.0) goto 999
         call prb(fb_i,wsstk_i,dist_i,xfinb_o,zfinb_o,zb_o)
         write(*,'(i8,1x,es20.12)') icase,zb_o
         goto 40
      endif
c
      if(mode.eq.5)then
 50      read(*,*,iostat=ios) icase,zfinp_i,fb_i,wsstk_i,hs_i,hmix_i,
     &                      ta_i,ptginv_i,ti_i
         if(ios.ne.0) goto 999
         call prfpp(zfinp_i,fb_i,wsstk_i,hs_i,hmix_i,ta_i,ptginv_i,ti_i,
     &              fmix_o,hmax_o)
         write(*,'(i8,3(1x,es20.12))') icase,zfinp_i,fmix_o,hmax_o
         goto 50
      endif
c
      if(mode.eq.6)then
 60      read(*,*,iostat=ios) icase,diam_i,vexit_i,tstak_i,dtemp_i,
     &                      temp_i,fmfpt1_i
         if(ios.ne.0) goto 999
         call p7n_flux(diam_i,vexit_i,tstak_i,dtemp_i,temp_i,fmfpt1_i,
     &                 fluxb_o,fluxm_o)
         write(*,'(i8,2(1x,es20.12))') icase,fluxb_o,fluxm_o
         goto 60
      endif
c
 70   continue
      read(*,*,iostat=ios) icase,(st(i),i=1,21)
      if(ios.ne.0) goto 999
      istype=INT(st(1))
      ipnum=1
      idw0(1)=INT(st(2))
      imet=INT(st(3))
      mrise=INT(st(4))
      mshear=INT(st(5))
      dist_i=st(6)
      zfinal(1)=st(7)
      zfrise=st(8)
      ht0(1)=st(9)
      diam0(1)=st(10)
      exitw0(1)=st(11)
      ws0(1)=st(12)
      istab0(1)=INT(st(13))
      sqrts0(1)=st(14)
      fm(1)=st(15)
      xmfin(1)=st(16)
      zmfin(1)=st(17)
      fb(1)=st(18)
      xbfin(1)=st(19)
      zbfin(1)=st(20)
      stipdw(1)=st(21)
      call grise(dist_i,htgrise_o,risefac_o)
      write(*,'(i8,2(1x,es20.12))') icase,htgrise_o,risefac_o
      goto 70
c
 999  continue
      end
c-----------------------------------------------------------------------
      subroutine prshear(fb,wsstk,plexp,hs,x,xfinb,zfinb,risesh)
c-----------------------------------------------------------------------
c --- Stub for a unit this round does NOT port (MSHEAR=1 is off for the
c     locked deck). A parity case must never reach it.
      real fb,wsstk,plexp,hs,x,xfinb,zfinb,risesh
      write(*,*) 'P7N oracle: PRSHEAR must not be called'
      stop 9
      end
c-----------------------------------------------------------------------
      subroutine prss(xarg,zly,r0,ws,istab,sqrts,diam,vexit,
     &                fluxm,fluxb,xfinm,xfinb,ssrise)
c-----------------------------------------------------------------------
c --- Stub for the Schulman-Scire downwash rise (method 2).
      real xarg,zly,r0,ws,sqrts,diam,vexit,fluxm,fluxb,xfinm,xfinb
      real ssrise
      integer istab
      write(*,*) 'P7N oracle: PRSS must not be called'
      stop 9
      end
c-----------------------------------------------------------------------
      subroutine prtab(xarg,zstart,nt,x,z,rise)
c-----------------------------------------------------------------------
c --- Stub for the tabulated rise (method 3 / area sources).
      real xarg,zstart,x,z,rise
      integer nt
      write(*,*) 'P7N oracle: PRTAB must not be called'
      stop 9
      end
c-----------------------------------------------------------------------
      subroutine prbl(xarg,xshift,ntab,xtab,ztab,blrise)
c-----------------------------------------------------------------------
c --- Stub for the buoyant LINE source rise.
      real xarg,xshift,xtab,ztab,blrise
      integer ntab
      write(*,*) 'P7N oracle: PRBL must not be called'
      stop 9
      end
c-----------------------------------------------------------------------
      subroutine intertab(val,nt,tab,i,j,fac)
c-----------------------------------------------------------------------
c --- Stub for the rise-table interpolation.
      real val,tab,fac
      integer nt,i,j
      write(*,*) 'P7N oracle: INTERTAB must not be called'
      stop 9
      end
